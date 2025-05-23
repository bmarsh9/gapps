from flask import abort, flash, redirect, url_for, session, current_app
from app.utils.decorators import custom_login
from app.models import db, User
from app.utils import misc


class UserFlow:
    """Handles different user authentication flows: login, register, accept."""

    VALID_FLOW_TYPES = ["login", "register", "accept"]
    PROVIDERS = ["local", "google", "microsoft"]

    def __init__(self, user_info, flow_type, provider, next_page=None):
        """
        user_info: user info that is provided by the provider
        flow_type: describes the user flow type - see VALID_FLOW_TYPES
        provider: valid provider - see PROVIDERS
        next_page: next page to redirect, expects url_for(<path>)
        """
        self.user_info = user_info
        self.user_dict = {}
        self.flow_type = flow_type
        self.provider = provider
        self.next_page = next_page

        self.validate_flow()
        self.validate_provider()

        # Normalize different user_info into common schema
        if provider == "google":
            self.parse_google_info()
        elif provider == "microsoft":
            self.parse_microsoft_info()
        else:
            self.parse_local_info()

    def parse_google_info(self):
        self.user_dict = {
            "email": self.user_info.get("email"),
            "first": self.user_info.get("given_name"),
            "last": self.user_info.get("family_name"),
        }
        if not self.user_dict["email"]:
            abort(422, "Missing required field: email")

    def parse_microsoft_info(self):
        self.user_dict = {
            "email": self.user_info.get("email"),
            "first": self.user_info.get("name"),
            "last": None,
        }
        if not self.user_dict["email"]:
            abort(422, "Missing required field: email")

    def parse_local_info(self):
        self.user_dict = {
            "email": self.user_info.get("email"),
            "first": self.user_info.get("first_name"),
            "last": self.user_info.get("last_name"),
            "password": self.user_info.get("password"),
            "password2": self.user_info.get("password2"),
        }
        if not self.user_dict["email"]:
            abort(422, "Missing required field: email")

        if not self.user_dict["password"]:
            abort(422, "Missing required field: password")

        if self.flow_type == "register":
            if self.user_dict["password"] != self.user_dict["password2"]:
                abort(422, "Passwords do not match")

    def validate_flow(self):
        if self.flow_type not in self.VALID_FLOW_TYPES:
            abort(422, "Invalid flow type")

    def validate_provider(self):
        if self.provider not in self.PROVIDERS:
            abort(422, "Invalid provider")

    def handle_flow(self, attributes={}):
        """Routes authentication based on flow type."""
        if self.flow_type == "login":
            return self._handle_login()
        elif self.flow_type == "register":
            return self._handle_register(**attributes)
        elif self.flow_type == "accept":
            return self._handle_accept(**attributes)
        abort(403, "Invalid authentication flow")

    def _handle_login(self, user=None):
        """Handles login flow."""
        if user is None:
            user = User.find_by_email(self.user_dict["email"])

        if not user:
            # If user does not exist but self-service registration is enabled, redirect
            if current_app.is_self_registration_enabled:
                flash("Unable to find account. Please create one.", "warning")
                return redirect(url_for("auth.get_register", provider=self.provider))
            abort(403, "Unable to find account. Registration is disabled.")

        if self.provider == "local" and not user.check_password(
            self.user_dict["password"]
        ):
            abort(403, "Invalid password")

        custom_login(user)

        # Have user create tenant if they don't have any
        if get_started := self.should_we_create_tenant(user):
            return get_started

        return redirect(self.next_page or url_for("main.home"))

    def _handle_register(self):
        """
        Handles self-service registration flow. This flow will only be used
        when self-service registration is enabled (current_app.is_self_registration_enabled).
        If the user already exists, we will follow the login path. If the user does not exist,
        we will create a new user and follow the login path.
        """
        if not current_app.is_self_registration_enabled:
            abort(403, "Self-service registration is disabled")

        # User already exists, follow login path
        if user := User.find_by_email(self.user_dict["email"]):
            abort(403, "User already exists. Please login or reset your password.")

        if self.provider == "local":
            if not misc.perform_pwd_checks(
                self.user_dict.get("password"),
                password_two=self.user_dict.get("password2"),
            ):
                abort(403, "Password does not meet requirements")

        user_object = {
            "email": self.user_dict["email"],
            "first_name": self.user_dict["first"],
            "last_name": self.user_dict["last"],
            "password": self.user_dict.get("password", None),
            "confirmed": False,
            "return_user_object": True,
        }
        if self.provider != "local":
            user_object["confirmed"] = True

        user = User.add(**user_object)
        return self._handle_login(user)

    def _handle_accept(self, token):
        """Handles user accepting tenant invite flow."""
        if not (result := User.verify_invite_token(token)):
            abort(403, "Invalid or expired invite token")

        if not (user := User.find_by_email(result.get("email"))):
            abort(403, "Invalid token: email not found")

        user.first_name = self.user_dict["first"] or user.first_name
        user.last_name = self.user_dict["last"] or user.last_name

        # For local provider, we set up the users password
        if self.provider == "local":
            if not misc.perform_pwd_checks(
                self.user_dict.get("password"),
                password_two=self.user_dict.get("password2"),
            ):
                flash("Password does not meet requirements", "warning")
                return redirect(url_for("auth.get_accept", token=token))
            user.set_password(self.user_dict.get("password"), set_pwd_change=True)
            user.set_confirmation()

        db.session.commit()
        custom_login(user)
        return redirect(self.next_page or url_for("main.home"))

    def should_we_create_tenant(self, user):
        if not user.get_tenants():
            return redirect(url_for("auth.get_started"))
        return False
