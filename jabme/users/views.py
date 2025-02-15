import json
import re
from datetime import date

import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import models
from fake_useragent import UserAgent
from rest_framework.response import Response
from rest_framework.views import APIView

PINCODE_REGEX = "^[1-9][0-9]{5}$"
User = get_user_model()


def validate_pincode(pin):
    reg = re.compile(PINCODE_REGEX)
    if not reg.match(pin):
        raise ValidationError("Enter correct pincode")


class RegisterView(APIView):
    def post(self, request):
        data = request.data

        try:
            user = User.objects.get(email=data["email"])
            return Response("Email Already exists.")
        except Exception:
            user = User()
            try:
                validate_pincode(data["pincode"])
            except Exception:
                return Response("Incorrect pincode")
            try:
                user.password = make_password(
                    BaseUserManager().make_random_password()
                )
                user.email = data["email"]
                user.name = data["name"]
                user.pincode = data["pincode"]
                user.district = data["district"]
                user.district_id = data["district_id"]
                user.age_category = data["category"]
                if "fcm_token" in data:
                    user.fcm_token = data["fcm_token"]
                user.save()
            except Exception:
                return Response("Exception occured, enter correct data")

        return Response("Registered Successfully")


class FindSlotView(APIView):
    def get(self, request):
        district_ids = (
            User.objects.filter()
            .values("district_id")
            .annotate(n=models.Count("pk"))
        )
        user_agent = UserAgent()
        today = date.today().strftime("%d-%m-%Y")
        result = []
        for district in district_ids:
            four5 = []
            eighteen = []
            headers = {"User-Agent": user_agent.random}
            url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={district['district_id']}&date={today}"
            r = requests.get(url, headers=headers).text
            r = json.loads(r)
            if "centers" in r:
                for center in r["centers"]:
                    for session in center["sessions"]:
                        if (
                            session["min_age_limit"] == 45
                            and session["available_capacity"] > 0
                        ):
                            four5.append(
                                {
                                    "name": center["name"],
                                    "date": session["date"],
                                    "slots": session["slots"],
                                    "vaccine": session["vaccine"],
                                    "availability": session[
                                        "available_capacity"
                                    ],
                                    "address": center["address"],
                                    "block_name": center["block_name"],
                                    "fee_type": center["fee_type"],
                                    "min_age_limit": session["min_age_limit"],
                                }
                            )
                        elif (
                            session["min_age_limit"] == 18
                            and session["available_capacity"] > 0
                        ):
                            eighteen.append(
                                {
                                    "name": center["name"],
                                    "date": session["date"],
                                    "slots": session["slots"],
                                    "vaccine": session["vaccine"],
                                    "availability": session[
                                        "available_capacity"
                                    ],
                                    "address": center["address"],
                                    "block_name": center["block_name"],
                                    "fee_type": center["fee_type"],
                                    "min_age_limit": session["min_age_limit"],
                                }
                            )
            else:
                break
            emails45 = User.objects.filter(
                district_id=district["district_id"], age_category="45+"
            ).values("email", "name")
            emails1844 = User.objects.filter(
                district_id=district["district_id"], age_category="18-44"
            ).values("email", "name")
            if eighteen or four5:
                if eighteen and four5:
                    if emails1844.exists() and emails45.exists():
                        result.append(
                            {
                                "district_id": district["district_id"],
                                "emails45+": emails45,
                                "data45+": four5,
                                "emails18-44": emails1844,
                                "data18-44": eighteen,
                            }
                        )
                    elif emails1844.exists() and not emails45.exists():
                        result.append(
                            {
                                "district_id": district["district_id"],
                                "emails18-44": emails1844,
                                "data18-44": eighteen,
                            }
                        )
                    elif emails45.exists() and not emails1844.exists():
                        result.append(
                            {
                                "district_id": district["district_id"],
                                "emails45+": emails45,
                                "data45+": four5,
                            }
                        )
                elif eighteen and not four5:
                    if emails1844.exists():
                        result.append(
                            {
                                "district_id": district["district_id"],
                                "emails18-44": emails1844,
                                "data18-44": eighteen,
                            }
                        )
                elif four5 and not eighteen:
                    if emails45.exists():
                        result.append(
                            {
                                "district_id": district["district_id"],
                                "emails45+": emails45,
                                "data45+": four5,
                            }
                        )

        return Response(result)
