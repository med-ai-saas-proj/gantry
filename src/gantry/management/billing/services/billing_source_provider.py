from gantry.shared.custom_types.error_exception import (
    ExternalAPIError,
    NotImplementedError,
)

from abc import ABC, abstractmethod

from pyrusult import Result


class BillingSourceProviderInterface(ABC):
    @abstractmethod
    async def createCustomer(self, req) -> Result[str, ExternalAPIError]:
        pass

    @abstractmethod
    async def deleteCustomer(
        self, provider_id: str
    ) -> Result[None, ExternalAPIError | NotImplementedError]:
        pass

    @abstractmethod
    async def updateCustomer(
        self, provider_id: str, req
    ) -> Result[None, ExternalAPIError | NotImplementedError]:
        pass

    @abstractmethod
    async def createSetupIntent(
        self, provider_id: str
    ) -> Result[dict, ExternalAPIError | NotImplementedError]:
        pass

    @abstractmethod
    async def listRequiredActionSetupIntents(
        self, provider_id: str
    ) -> Result[list, ExternalAPIError | NotImplementedError]:
        pass

    @abstractmethod
    async def cancelSetupIntent(
        self, setup_intent_id: str
    ) -> Result[None, ExternalAPIError | NotImplementedError]:
        pass

    @abstractmethod
    async def listPaymentMethods(
        self, provider_id: str
    ) -> Result[list, ExternalAPIError | NotImplementedError]:
        pass

    @abstractmethod
    async def getPaymentMethod(
        self, payment_method_id: str
    ) -> Result[dict, ExternalAPIError | NotImplementedError]:
        pass

    @abstractmethod
    async def detachPaymentMethod(
        self, payment_method_id: str
    ) -> Result[None, ExternalAPIError | NotImplementedError]:
        pass
