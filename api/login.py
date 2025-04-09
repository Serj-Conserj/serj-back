import os
from config import telegram_token, telegram_login, jwt_secret
from fastapi import APIRouter, Depends, Request, status
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.templating import Jinja2Templates

from typing import Optional
from pydantic import BaseModel
import hashlib
import hmac
import time
from enum import Enum
import jwt

router = APIRouter()


class Size(Enum):
    """Button Size variants"""

    LARGE: str = "large"
    MEDIUM: str = "medium"
    SMALL: str = "small"


class TelegramLoginWidget:
    """
    Class to generate Telegram login Widget according to the information
    from the official documentation: https://core.telegram.org/widgets/login

    :param size: enum [Size.LARGE | Size.MEDIUM | Size.SMALL]
    :param user_photo: bool
    :param corner_radius: integer
    :param access_write: bool
    """

    def __init__(
        self,
        telegram_login: str,
        size: Size = Size.MEDIUM,
        user_photo: bool = False,
        corner_radius: Optional[int] = None,
        access_write: bool = True,
    ):
        self.telegram_login = telegram_login
        self.corner_radius = corner_radius
        self.size = size
        self.user_photo = user_photo
        self.access_write = access_write
        self.start_script = (
            "<script async src=" '"https://telegram.org/js/telegram-widget.js?22"'
        )
        self.end_script = "></script>"

    def callback_telegram_login_widget(self, func: str, arg: str = "") -> str:
        """
        Generate Telegram Callback Login Widget.

        :param str func: - JS function that have to call
        :param str arg: - argument for JS function

        If authorization was successful, the method waits for the Javascript
        function to be called.
        Example:
        callback_telegram_login_widget
        widget = callback_telegram_login_widget(func='onTelegramAuth',
                                                arg='user')

        Put this code to your HTML template:
            <script type="text/javascript">
            function onTelegramAuth(user) {
            alert(
            'Logged in as ' + user.first_name + ' ' + user.last_name + '!');
            }
            </script>

        :return str: Return JS code with widget
        """
        data_on_auth = f'data-onauth="{func}({arg})"'

        params = self._generate_params(
            self.telegram_login,
            self.size,
            self.corner_radius,
            self.user_photo,
            self.access_write,
        )
        return (
            f"{self.start_script} "
            f'{params.get("data_telegram_login")} '
            f'{params.get("data_size")} '
            f"{data_on_auth} "
            f'{params.get("data_user_pic")} '
            f'{params.get("data_radius")} '
            f'{params.get("data_request_access")} '
            f"{self.end_script}"
        )

    def redirect_telegram_login_widget(self, redirect_url: str):
        """
        Generate Telegram Callback Login Widget
        :param str redirect_url: - The URL to which the redirection
                                      should take for authorization.

        :return str: Return JS code with widget
        """

        params = self._generate_params(
            self.telegram_login,
            self.size,
            self.corner_radius,
            self.user_photo,
            self.access_write,
        )
        return (
            f"{self.start_script} "
            f'{params.get("data_telegram_login")} '
            f'{params.get("data_size")} '
            f'data-auth-url="{redirect_url}" '
            f'{params.get("data_user_pic")} '
            f'{params.get("data_radius")} '
            f'{params.get("data_request_access")} '
            f"{self.end_script}"
        )

    def _generate_params(
        self,
        telegram_login: str,
        size: Size,
        corner_radius: Optional[int] = None,
        user_photo: bool = False,
        access_write: bool = True,
    ):
        """
        :param str telegram_login:
        :param Size size:
        :param int| None corner_radius:
        :param bool user_photo:
        :param bool access_write:
        :return: str
        """
        data_telegram_login = f'data-telegram-login="{telegram_login}"'
        data_size = f'data-size="{size.value}"'
        data_userpic = f'data-userpic="{user_photo}"' if not user_photo else ""
        data_radius = (
            f'data-radius="{corner_radius}"' if isinstance(corner_radius, int) else ""
        )
        data_request_access = f'data-request-access="{access_write}"'

        return {
            "data_telegram_login": data_telegram_login,
            "data_size": data_size,
            "data_user_pic": data_userpic,
            "data_radius": data_radius,
            "data_request_access": data_request_access,
        }


class TelegramAuth(BaseModel):
    id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None
    auth_date: Optional[str] = None
    hash: Optional[str] = None


def validate_telegram_data(telegram_bot_token: str, data: TelegramAuth) -> dict:
    """
    Checking the authorization telegram data according to the information.
    Official telegram doc: https://core.telegram.org/widgets/login

    Example of incoming data for validation:
        https://localhost/login?
        id=245942576&
        first_name=Pavel&
        last_name=Glukhov&
        username=Gluuk&
        photo_url=https%3A%2F%2Ft.me%2Fi%2Fuserpic%2F320%2F0hxupwk8k7ZrvTyRMSEk83gQax0UFTGkhZzN-NPKIAk.jpg&
        auth_date=1688449915&hash=9f1a28d6e929af7e314b634df2a8dbb78460ef409368ac58c809c48dd9a4d367&
        hash=9f1a28d6e929af7e314b634df2a8dbb78460ef409368ac58c809c48dd9a4d367

    :param telegram_bot_token:
    :param data:
    :return:
    """
    data = data.model_dump()
    received_hash = data.pop("hash", None)
    auth_date = data.get("auth_date")

    if _verify_telegram_session_outdate(auth_date):
        raise Exception("Telegram authentication session is expired.")

    generated_hash = _generate_hash(data, telegram_bot_token)

    # if generated_hash != received_hash:
    #     raise Exception("Request data is incorrect")

    return data


def _verify_telegram_session_outdate(auth_date: str) -> bool:
    # one_day_in_second = 86400
    # unix_time_now = int(time.time())
    # unix_time_auth_date = int(auth_date)
    # timedelta = unix_time_now - unix_time_auth_date

    # if timedelta > one_day_in_second:
    #     return True
    # return False
    return False


def _generate_hash(data: dict, token: str) -> str:
    request_data_alph_sorted = sorted(data.items(), key=lambda v: v[0])

    data_check_string = "\n".join(
        f"{key}={value}" for key, value in request_data_alph_sorted
    )

    secret_key = hashlib.sha256(token.encode()).digest()
    generated_hash = hmac.new(
        key=secret_key, msg=data_check_string.encode(), digestmod=hashlib.sha256
    ).hexdigest()

    return generated_hash


templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
)


def create_jwt_token(query_params):
    payload = {
        "sub": query_params.id,
        "first_name": query_params.first_name,
        "auth_date": query_params.auth_date,
    }
    token = jwt.encode(payload=payload, key=jwt_secret, algorithm="HS256")
    return token


def set_cookies():

    pass


@router.get("/login", name="login")
async def login(
    request: Request,
    query_params: TelegramAuth = Depends(TelegramAuth),
):
    login_widget = TelegramLoginWidget(
        telegram_login=telegram_login,
        size=Size.LARGE,
        user_photo=False,
        corner_radius=0,
    )

    redirect_url = str(request.url_for("login"))
    redirect_widget = login_widget.redirect_telegram_login_widget(
        redirect_url=redirect_url
    )

    if not query_params.model_dump().get("hash"):
        # return templates.TemplateResponse(
        #     "login.html",
        #     context={
        #         "request": request,
        #         "redirect_telegram_login_widget": redirect_widget,
        #     },
        # )
        return {"vd": validated_data}

    try:
        validated_data = validate_telegram_data(telegram_token, query_params)
        if validated_data:
            create_jwt_token(query_params)
            set_cookies()
            # return templates.TemplateResponse(
            #     "profile.html", context={"request": request, **validated_data}
            # )
            return {"vd": validated_data}
    except Exception as e:
        print(e)
