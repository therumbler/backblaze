from typing import cast, TYPE_CHECKING

from .base import BaseKey
from ..models.key import KeyModel
from ..decorators import authorize_required

if TYPE_CHECKING:
    from .. import Blocking


class BlockingKey(BaseKey):
    _context: "Blocking"

    @authorize_required
    def delete(self) -> KeyModel:
        """Used delete key.

        Returns
        -------
        KeyModel
            Details on delete key.
        """

        return KeyModel(
            cast(
                dict,
                self._context._post(
                    url=self._context._routes.key.delete,
                    json={"applicationKeyId": self.key_id},
                    include_account=False
                )
            )
        )
