import json
from dataclasses import asdict
from time import sleep

import requests

from home_data import Rentals


class ServerError(Exception):
    pass


class Parser:
    HEADERS = {
        "authority": "api.qasa.se",
        "accept": "*/*",
        "accept-language": "ru-RU,ru;q=0.9,uk-UA;q=0.8,uk;q=0.7,en-US;q=0.6,en;q=0.5",
        "content-type": "application/json",
        "origin": "https://bostad.blocket.se",
        "referer": "https://bostad.blocket.se/",
        "sec-ch-ua": '"Chromium";v="110", "Not A(Brand";v="24", "Google Chrome";v="110"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    }

    @staticmethod
    def get_json_data(offset: int = 0) -> dict:
        return {
            'operationName': 'HomeSearchQuery',
            'variables': {
                'limit': 50,
                'platform': 'blocket',
                'searchParams': {
                    'areaIdentifier': [],
                    'rentalType': [
                        'long_term'
                    ],
                },
                'offset': offset,
                'order': 'DESCENDING',
                'orderBy': 'PUBLISHED_AT',
            },
            'query': 'query HomeSearchQuery($offset: Int, $limit: Int, $platform: PlatformEnum, $order: HomeSearchOrderEnum, $orderBy: HomeSearchOrderByEnum, $searchParams: HomeSearchParamsInput!) {\n  homeSearch(\n    platform: $platform\n    searchParams: $searchParams\n    order: $order\n    orderBy: $orderBy\n  ) {\n    filterHomesOffset(offset: $offset, limit: $limit) {\n      pagesCount\n      totalCount\n      hasNextPage\n      hasPreviousPage\n      nodes {\n        id\n        firsthand\n        rent\n        tenantBaseFee\n    qasaGuaranteeCost\n        title\n        landlord {\n          uid\n          companyName\n          __typename\n        }\n    homeTemplates {\n        id\n        type\n        squareMeters\n           roomCount\n        rent\n        description\n        traits {\n        type\n        __typename\n      }\n        __typename\n        }\n        location {\n          id\n          latitude\n          longitude\n        locality\n        route\n        postalCode\n        streetNumber\n          __typename\n        }\n        type\n        duration {\n          createdAt\n          id\n        updatedAt\n        startOptimal\n          __typename\n        }\n        corporateHome\n        uploads {\n          id\n          url\n          __typename\n        }\n        numberOfHomes\n        minRoomCount\n        maxRoomCount\n        minSquareMeters\n        maxSquareMeters\n        rentalType\n        tenantCount\n        __typename\n      }\n      __typename\n    }\n    __typename\n  }\n}\n',
        }

    @staticmethod
    def house_parser(house: dict) -> dict:
        location = house["location"]
        home_template = house["homeTemplates"][0]
        traits = [convenience["type"] for convenience in home_template["traits"]]

        def indentify_available_date():
            date = house.get("duration").get("startOptimal")

            return date.split("T")[0] if date else ""

        def identify_property_type():
            if house["tenantCount"] == 1:
                return "room"

            return "apartment" if house["type"] == "apartment" else "house"

        result = Rentals(
            external_source="BlocketSpider",
            external_link=f"https://bostad.blocket.se/p2/sv/home/{house['id']}",
            external_id=house["id"],
            city=location["locality"],
            zipcode=location["postalCode"],  # !!!!!
            house_number=location["streetNumber"],
            street=location["route"],
            latitude=str(location["latitude"]),
            longitude=str(location["longitude"]),
            description=home_template["description"],
            property_type=identify_property_type(),  # !!!!!
            room_count=int(home_template["roomCount"]),
            square_meters=home_template["squareMeters"],
            available_date=indentify_available_date(),
            rent=home_template["rent"],
            agency_fee=house["tenantBaseFee"],
            deposit=house["qasaGuaranteeCost"],
            facilities=traits,
            images=[i["url"] for i in house.get("uploads")],
            landlord_name="Blocket",
            landlord_email="ovrigt@blocket.se",
        )

        return asdict(result)


class AllPageParser(Parser):

    def __init__(self, *, limit: int = None):
        self.offset = 0
        self.json_data = self.get_json_data()
        if limit:
            self.limit = limit * 50

    def send_api_request(self, data=None):

        if not data:
            data = self.json_data

        response = requests.post(
            "https://api.qasa.se/graphql", headers=self.HEADERS, json=data
        )

        if response.status_code == 200:
            return response.json()

        raise ServerError(f"Something wen wrong {response.status_code}")

    def get_page_data(self, offset: int = 0) -> dict:

        json_data = self.get_json_data(offset)
        response = self.send_api_request(data=json_data)

        return response["data"]["homeSearch"]["filterHomesOffset"]

    def all_pages_data(self):

        data = self.get_page_data()

        result = [*data["nodes"]]
        page_count = data["pagesCount"]
        end = data["totalCount"]

        while self.offset < end:

            sleep(1)

            print(f"Parsing {int(self.offset / 50 + 1)} page of {page_count}")

            self.offset += 50
            data = self.get_page_data()
            result.extend(data["nodes"])

            if self.offset > self.limit:
                break

        return result

    def parse_all_data(self) -> [dict]:
        result = []
        houses_data = [self.house_parser(house) for house in self.all_pages_data()]

        for i, house in enumerate(houses_data):
            house["position"] = i
            result.append(house)

        return result

    def write_to_json(self):
        with open("BlocketSpider.json", "w") as file:
            json.dump(self.parse_all_data(), fp=file, indent=2)
