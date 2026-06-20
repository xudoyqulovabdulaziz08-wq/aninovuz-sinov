from aiogram import Router

from handlers import(
    start
)






main_router = Router()



main_router.include_routers(

    start.router


)