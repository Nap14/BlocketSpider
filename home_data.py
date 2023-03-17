from dataclasses import dataclass, field


@dataclass
class Rentals:
    external_source: str
    external_source: str
    external_link: str
    external_id: int
    city: str
    zipcode: str
    address: str = field(init=False)
    title: str = field(init=False)
    street: str = field(repr=False)
    house_number: str = field(repr=False)
    latitude: str
    longitude: str
    description: str
    property_type: str
    room_count: int
    square_meters: float
    available_date: str
    rent: int
    agency_fee: int
    deposit: int
    facilities: [str]
    images: [str]
    landlord_name: str
    landlord_email: str

    def __post_init__(self):
        self.address = f'{self.street}, {self.house_number}, {self.zipcode}, {self.city}'
        self.title = self.address

    def __eq__(self, other):
        if isinstance(other, Rentals):
            return self.external_id == other.external_id
        return False

