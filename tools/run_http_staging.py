import requests
from app.core.config import get_settings
from app.security.tokens import create_access_token
s=get_settings(); token=create_access_token('staging-admin',s.jwt_secret,role='ADMIN')
h={'Authorization':f'Bearer {token}'}
out={}
for name,path,mime in [('pdf','tests/fixtures/content_upload_test_book_fa.pdf','application/pdf'),('docx','tests/fixtures/content_upload_test_book_fa.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document')]:
 with open(path,'rb') as f:
  r=requests.post('http://localhost:8001/api/v1/admin/content/upload',headers=h,files={'file':(path,f,mime)},data={'title':'HTTP Staging Book '+name,'grade':'10','subject':'فیزیک','chapter_title':'فصل اول','lesson_title':'درس اول'})
 out[name]={'status':r.status_code,'body':r.json() if r.headers.get('content-type','').startswith('application/json') else r.text[:200]}
with open('tests/fixtures/content_upload_test_book_fa.pdf','rb') as f:
 r=requests.post('http://localhost:8001/api/v1/admin/content/upload',headers=h,files={'file':('x.txt',f,'text/plain')},data={'title':'bad','grade':'10','subject':'x'})
 out['invalid_mime']=r.status_code
print(out)
