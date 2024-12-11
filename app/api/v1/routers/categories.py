from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, UploadFile
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates("templates")
router = APIRouter()

# @router.get("/update")
# async def update_categories_file():
#     ...

@router.get("/get")
async def get_tree(request):
    with open("cat_tree.json", "r") as file:
        dumped_data = file.read()

    return templates.TemplateResponse(
        "tree.html",
        {
            "request": request,
            "data": dumped_data
        }
    )





