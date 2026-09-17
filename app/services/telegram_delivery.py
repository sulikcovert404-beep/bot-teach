from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TelegramDelivery:
 method: str
 payload: dict[str, object]
def build_delivery(*, asset_type, chat_id, content, caption):
 if not content.strip(): raise ValueError('MISSING_ASSET')
 if asset_type=='PODCAST': return TelegramDelivery('sendAudio',{'chat_id':chat_id,'audio':content,'caption':caption})
 if asset_type=='PDF': return TelegramDelivery('sendDocument',{'chat_id':chat_id,'document':content,'caption':caption})
 return TelegramDelivery('sendMessage',{'chat_id':chat_id,'text':content})
async def deliver_assets(bot, chat_id, assets, *, allow_placeholders: bool = False):
 for a in assets:
  if not a.content.strip(): raise ValueError('MISSING_ASSET')
  if getattr(a, 'is_placeholder', False) and not allow_placeholders: raise PermissionError('PLACEHOLDER_ASSET_NOT_DELIVERABLE')
  if a.asset_type=='PODCAST': await bot.send_audio(chat_id,a.content,caption=a.caption)
  elif a.asset_type=='PDF': await bot.send_document(chat_id,a.content,caption=a.caption)
  else: await bot.send_text(chat_id,a.content)
def validate_asset_access(*, review_state, tenant_id, requested_tenant_id, lesson_id, requested_lesson_id, grade=None, requested_grade=None):
 if review_state!='APPROVED': raise PermissionError('UNAPPROVED_ASSET')
 if tenant_id is None or requested_tenant_id is None or tenant_id!=requested_tenant_id: raise PermissionError('WRONG_TENANT')
 if lesson_id!=requested_lesson_id: raise PermissionError('WRONG_LESSON')
 if grade is not None or requested_grade is not None:
  if grade is None or requested_grade is None or grade!=requested_grade: raise PermissionError('WRONG_GRADE')

class TelegramMediaSender(Protocol):
 async def send_audio(self, chat_id: int, audio: str, *, caption: str | None = None) -> None: ...
 async def send_document(self, chat_id: int, document: str, *, caption: str | None = None) -> None: ...
 async def send_text(self, chat_id: int, text: str, *, reply_markup: dict[str, object] | None = None) -> None: ...


