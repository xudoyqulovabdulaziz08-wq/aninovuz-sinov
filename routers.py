from aiogram import Router

from handlers import(
    start,
    search,
    qollanma,
    reklama,
    buy_vip,
    help,
    admin_menu,
    creator_menu
)
from handlers.admin_panel.admin_anime import(
    anime_menu,
    add_anime,
    list_anime,
    janr,
    add_episode,
    del_episode
)
from handlers.admin_panel.admin_channel import(
    channel_menu,
    add_channel,
    list_channel
)
from handlers.admin_panel.admin_advert import(
    admin_advet_menu
)
from handlers.admin_panel.admin_vip import(
    admin_vip_menu
)



main_router = Router()



main_router.include_routers(

    start.router,
    creator_menu.router,

    admin_menu.router,

    anime_menu.router,
    channel_menu.router,
    admin_advet_menu.router,
    admin_vip_menu.router,
    add_anime.router,
    list_anime.router,
    janr.router,
    add_episode.router,
    del_episode.router,

    add_channel.router,
    list_channel.router,

    qollanma.router,
    reklama.router,
    buy_vip.router,
    help.router,


    search.router

)