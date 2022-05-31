import requests
import json
import base64

# запит для перевірки поточного статусу API 

apiUrl = "https://search4faces.com/api/json-rpc/v1"
apiKey = "a17a88-818606-dba935-3fa2b3-e39076"

def api_s4f_check(apiUrl, apiKey):
    headers = ({'content-type': 'application/json',
                "x-authorization-token": apiKey})
        
    payload = {
            
        "jsonrpc": "2.0",
         "method": "rateLimit",
        "id": "some-id",
        "params": {}
            
        }
    response = requests.post(
        apiUrl, data=json.dumps(payload), headers=headers).json()
    
    return response['result']

def search_face(face_parameter, image_name, apiUrl, apiKey):
    global solution
    solution = ''
    headers = ({'content-type': 'application/json',
               "x-authorization-token": apiKey})
    # Example echo method
    payload = {
        "jsonrpc": "2.0",
        "method": "searchFace",
        "id": "some-id",
        "params": {
            "image": image_name,
            "face": face_parameter,
            "source": "vk_wall",
            # vkok_avatar или vk_wall или tt_avatar(тік-ток) или ch_avatar(клабхауз) или ig_avatar(інста) (база данных для поиска)
            "hidden": True,
            "results": "10"
        },
        'id': 'some-id'
    }
    response = requests.post(
        apiUrl, data=json.dumps(payload), headers=headers).json()

    full_data = response["result"]["profiles"]
    i = 0

    while i != 10:
        solution = solution + str(full_data[i]['last_name']) + ' ' + str(full_data[i]['first_name']) + '  Співпадіння: ' + str(full_data[i]['score']) + '% ' + str(full_data[i]['maiden_name']) + ' Проживає - ' + str(full_data[i]['city']) + ' ' + str(full_data[i]['country']) + ' ' + str(full_data[i]['age']) + 'років ' + str(full_data[i]['born']) + ' ' + str(full_data[i]['profile'] + '\n')
        i = i+1
    #df = pd.DataFrame(response["result"]["profiles"])

def photo_search(imgname, apiUrl, apiKey):
   
    try:
        file_name_img = imgname
        with open(file_name_img, 'rb') as f:
            data = f.read()
        image_64_encode = base64.b64encode(data).decode("ascii")

        # токен даю поки свій, але бажано отримати новий
        headers = ({'content-type': 'application/json',
                "x-authorization-token": apiKey})

        # формування json запиту ()
        payload = {
            "jsonrpc": "2.0",
            "method": "detectFaces",
            "id": "some-id",
            "params": {
                "image": image_64_encode
            }
        }
        response = requests.post(
            apiUrl, data=json.dumps(payload), headers=headers).json()
        image_name = response["result"]['image']
        face_parameter = response["result"]['faces'][0]
        # print(face_parameter)
        search_face(face_parameter, image_name)
    # іноді буває так що сервіс ігнорить зображення потрібно ще раз перезакинути
    except IndexError:
        global solution
        solution = 'Нажаль не вдалось перевірити дане фото, спробуйте через 5 секунд знову (допоки переконайтесь в якості фото та що на зображені одне обличчя). Якщо це не допомагає ми не можемо розпізнати обличчя на даному фото'
    return solution


apiUrl = "https://search4faces.com/api/json-rpc/v1"
apiKey = "a17a88-818606-dba935-3fa2b3-e39076"  #76
print(api_s4f_check(apiUrl, apiKey))

