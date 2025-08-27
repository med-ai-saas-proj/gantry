from typing import Any
from src.entities import BaseEntity


class BrokerCredentials(BaseEntity):
    id: Any
    brokerName: Any
    credentials: Any
    createdAt: Any
    updatedAt: Any
