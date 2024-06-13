import base64
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import AllegroToken
from app.services.allegro_token import update_token_by_id


async def check_token(database: AsyncSession, token: AllegroToken):
    access_token = token.access_token
    headers = {

        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/vnd.allegro.public.v1+json',
    }
    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.allegro.pl/me', headers=headers) as res:
            if res.status == 200:
                print('API call successful, token is valid')
                return token
            elif res.status == 401:
                print('API call failed, token has expired, refreshing...')
                try:
                    new_access_token = await refresh_access_token(database, token)
                    print('Access token refreshed successfully')
                    return new_access_token
                except Exception as err:
                    print('Error refreshing access token:', err)
                    raise
            else:
                print('API call failed, token is invalid:', res.reason, res.status)
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
                print('Access token refreshed successfully')
                print("new access token: ", access_token)
                print("new refresh token: ", refresh_token)
                try:
                    token = await update_token_by_id(
                        database=database,
                        token_id=token.id_,
                        refresh_token=refresh_token,
                        access_token=access_token
                    )
                    print('New tokens saved to database successfully')
                    return token
                except Exception as error:
                    print('Error saving new tokens to database:', error)
                    raise Exception('Failed to save new tokens to database')
            else:
                print(f"Error refreshing access token: {res.status} {res.reason}")
                raise Exception('Failed to refresh access token')


# Example usage:
# access_token = asyncio.run(get_and_check_token())
# print(access_token)


# tokens = asyncio.run(get_and_check_token())
# print(tokens)
