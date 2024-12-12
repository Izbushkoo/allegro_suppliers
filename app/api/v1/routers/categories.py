from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, UploadFile
from fastapi.templating import Jinja2Templates
import json

templates = Jinja2Templates("templates")
router = APIRouter()

# @router.get("/update")
# async def update_categories_file():
#     ...

@router.get("/get")
async def get_tree(request: Request):
    with open("cat_tree.json", "r", encoding="utf-8") as file:
        data = json.loads(file.read())

    return templates.TemplateResponse(
        "tree.html",
        {
            "request": request,
            "data": data
        }
    )





