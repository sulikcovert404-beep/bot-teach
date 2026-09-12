import requests
from app.core.config import get_settings
from app.security.tokens import create_access_token
s=get_settings(); h={'Authorization':'Bearer '+create_access_token('staging-admin',s.jwt_secret,role='ADMIN')}
out={}
def post(fn,mime,title='HTTP final'):
 with open(fn,'rb') as f:
  return requests.post('http://localhost:8001/api/v1/admin/content/upload',headers=h,files={'file':(fn,f,mime)},data={'title':title,'grade':'10','subject':'فیزیک','chapter_title':'فصل اول','lesson_title':'درس اول'},timeout=10)
for k,fn,mi in [('pdf','tests/fixtures/content_upload_test_book_fa.pdf','application/pdf'),('docx','tests/fixtures/content_upload_test_book_fa.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document')]:
 r=post(fn,mi,'HTTP final '+k); out[k]={'status':r.status_code,'json':r.json()}
with open('tests/fixtures/content_upload_test_book_fa.pdf','rb') as f:
 r=requests.post('http://localhost:8001/api/v1/admin/content/upload',headers=h,files={'file':('x.pdf',f,'text/plain')},data={'title':'bad','grade':'10','subject':'x'},timeout=10); out['invalid_mime']=r.status_code
print(out)
