from clld import interfaces
from clld.db.meta import CustomModelMixin
from clld.db.models.common import Language
from clld_glottologfamily_plugin.models import HasFamilyMixin
from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
)
from zope.interface import implementer


# -----------------------------------------------------------------------------
# specialized common mapper classes
# -----------------------------------------------------------------------------
@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, Language, HasFamilyMixin):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
