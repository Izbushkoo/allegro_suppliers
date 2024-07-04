import base64
import aiohttp
import requests
from sqlalchemy.ext.asyncio import AsyncSession
import requests
import json
import time

from app.models.database_models import AllegroToken
from app.api.deps import SessionLocal
from app.services.allegro_token import update_token_by_id, update_token_by_id_sync, insert_token_sync
from app.schemas.pydantic_models import CallbackManager, InitializeAuth
from app.loggers import ToLog


CODE_URL = "https://allegro.pl/auth/oauth/device"
TOKEN_URL = "https://allegro.pl/auth/oauth/token"


async def check_token(database: AsyncSession, token: AllegroToken,
                      callback_manager: CallbackManager = CallbackManager()):
    access_token = token.access_token
    headers = {

        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/vnd.allegro.public.v1+json',
    }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.allegro.pl/me', headers=headers) as res:
            if res.status == 200:
                ToLog.write_basic('API call successful, token is valid')
                await callback_manager.send_ok_callback_async('API call successful, token is valid')
                return token
            elif res.status == 401:
                ToLog.write_basic('API call failed, token has expired, refreshing...')
                await callback_manager.send_ok_callback_async('API call failed, token has expired, refreshing...')
                try:
                    new_access_token = await refresh_access_token(database, token)
                    ToLog.write_basic('Access token refreshed successfully')
                    await callback_manager.send_ok_callback_async('Access token refreshed successfully')
                    return new_access_token
                except Exception as err:
                    ToLog.write_error(f'Error refreshing access token: {err}')
                    await callback_manager.send_error_callback_async(f'Error refreshing access token: {err}')
                    raise
            else:
                ToLog.write_error(f'API call failed, token is invalid: {res.reason} {res.status}')
                await callback_manager.send_error_callback_async(
                    f'API call failed, token is invalid: {res.reason} {res.status}'
                )
                raise Exception('Invalid access token')


async def refresh_access_token(database: AsyncSession, token: AllegroToken) -> AllegroToken:

    client_id = token.client_id
    client_secret = token.client_secret
    refresh_token = token.refresh_token

    auth_str = f'{client_id}:{client_secret}'
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {b64_auth_str}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'redirect_uri': token.redirect_url
    }
    async with aiohttp.ClientSession() as session:
        async with session.post('https://allegro.pl/auth/oauth/token', headers=headers, data=data) as res:
            body = await res.json()
            if res.status == 200:
                access_token = body['access_token']
                refresh_token = body['refresh_token']
                ToLog.write_basic('Access token refreshed successfully')
                # ToLog.write_basic(f"new access token: {access_token}")
                # ToLog.write_basic(f"new refresh token: {refresh_token}")
                try:
                    token = await update_token_by_id(
                        database=database,
                        token_id=token.id_,
                        refresh_token=refresh_token,
                        access_token=access_token
                    )
                    ToLog.write_basic('New tokens saved to database successfully')
                    return token
                except Exception as error:
                    ToLog.write_error(f'Error saving new tokens to database: {error}')
                    raise Exception('Failed to save new tokens to database')
            else:
                ToLog.write_error(f"Error refreshing access token: {res.status} {res.reason}")
                raise Exception('Failed to refresh access token')


def refresh_access_token_sync(database, token):
    client_id = token.client_id
    client_secret = token.client_secret
    refresh_token = token.refresh_token

    auth_str = f'{client_id}:{client_secret}'
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    headers = {
        'Authorization': f'Basic {b64_auth_str}',
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'redirect_uri': token.redirect_url
    }

    res = requests.post('https://allegro.pl/auth/oauth/token', headers=headers, data=data)
    body = res.json()

    if res.status_code == 200:
        access_token = body['access_token']
        refresh_token = body['refresh_token']
        ToLog.write_basic('Access token refreshed successfully')
        ToLog.write_basic(f"new access token: {access_token}")
        ToLog.write_basic(f"new refresh token: {refresh_token}")
        try:
            token = update_token_by_id_sync(
                database=database,
                token_id=token.id_,
                refresh_token=refresh_token,
                access_token=access_token
            )
            ToLog.write_basic('New tokens saved to database successfully')
            return token
        except Exception as error:
            ToLog.write_error(f'Error saving new tokens to database: {error}')
            raise Exception('Failed to save new tokens to database')
    else:
        ToLog.write_error(f"Error refreshing access token: {res.status_code} {res.reason}")
        raise Exception('Failed to refresh access token')


def check_token_sync(database, token):
    access_token = token.access_token
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/vnd.allegro.public.v1+json',
    }

    res = requests.get('https://api.allegro.pl/me', headers=headers)

    if res.status_code == 200:
        ToLog.write_basic('API call successful, token is valid')
        return token
    elif res.status_code == 401:
        ToLog.write_basic('API call failed, token has expired, refreshing...')
        try:
            new_access_token = refresh_access_token_sync(database, token)
            ToLog.write_basic('Access token refreshed successfully')
            return new_access_token
        except Exception as err:
            ToLog.write_error(f'Error refreshing access token: {err}')
            raise
    else:
        ToLog.write_error(f'API call failed, token is invalid: {res.reason} {res.status_code}')
        raise Exception('Invalid access token')


def get_code(client_id: str, client_secret: str):

    payload = {'client_id': client_id}
    headers = {'Content-type': 'application/x-www-form-urlencoded'}
    api_call_response = requests.post(CODE_URL, auth=(client_id, client_secret),
                                      headers=headers, data=payload, verify=False)
    return api_call_response.json()


def get_access_token(device_code, init_auth: InitializeAuth):
    try:
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'urn:ietf:params:oauth:grant-type:device_code', 'device_code': device_code}
        api_call_response = requests.post(TOKEN_URL, auth=(init_auth.client_id, init_auth.client_secret),
                                          headers=headers, data=data, verify=False)
        return api_call_response
    except requests.exceptions.HTTPError as err:
        raise err


def await_for_access_token(interval, device_code, init_auth: InitializeAuth):
    max_attempt = 30
    attempt = 0
    while attempt < max_attempt:
        time.sleep(interval)
        result_access_token = get_access_token(device_code, init_auth)
        token = json.loads(result_access_token.text)
        if result_access_token.status_code == 400:
            if token['error'] == 'slow_down':
                interval += interval
            if token['error'] == 'access_denied':
                break
            attempt += 1
        else:
            return token
    raise TimeoutError("too long wait till auth completed. Exited")


def initialize_auth(init_auth: InitializeAuth):
    callback_manager: CallbackManager = CallbackManager(
        url=init_auth.callback_url,
        resource_id=init_auth.user_id
    )
    try:
        code = get_code(init_auth.client_id, init_auth.client_secret)
    except Exception as err:
        ToLog.write_error(f"Code was not be received from allegro {err}")
        callback_manager.send_error_callback(f"Code was not be received from allegro {err}")
        raise err
    else:
        ToLog.write_basic(f"{code}")
        ToLog.write_basic(f"{type(code)}")
        callback_manager.send_ok_callback(code["verification_uri_complete"])
        try:
            token = await_for_access_token(int(code['interval']), code['device_code'], init_auth)
        except Exception as err:
            ToLog.write_error(f"Smth went wrong {err}")
            callback_manager.send_error_callback(f"Smth went wrong {err}")
        else:
            database = SessionLocal()
            allegro_token: AllegroToken = AllegroToken(
                belongs_to=init_auth.user_id,
                account_name=init_auth.account_name,
                description=init_auth.account_description,
                redirect_url="none",
                client_id=init_auth.client_id,
                client_secret=init_auth.client_secret,
                access_token=token["access_token"],
                refresh_token=token["refresh_token"]
            )
            try:
                insert_token_sync(database, allegro_token)
            except Exception as err:
                ToLog.write_error(f"Error during saving token to database {err}")
                callback_manager.send_error_callback(f"Error during saving token to database {err}")
            else:
                ToLog.write_basic(f"{allegro_token}")
                ToLog.write_basic(f"Token successfully added to database")
                callback_manager.send_finish_callback(f"Application authorized successfully")
