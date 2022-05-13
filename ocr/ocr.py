#тести
#!/usr/bin/python
# -*- coding: utf-8 -*-
'''
1 + водійське
2 + (низька роздільна здатність)водійське
3 + водійське
4 + (низька роздільна здатність)
5 +
6 + (низька роздільна здатність)
7 - (номер документа)
8 - (не витягує ім'я бо ocr не бачить)
9 - (не завжди визначає правильно дату народження) додДокумент
'''
from sqlite3 import paramstyle
import pytesseract 
from PIL import Image
import re

full_info = {}


def file_name(imgname):
    global full_info
    global param
    param = 1
    #print(imgname) '''назва файлу'''
    global img
    img = Image.open (imgname)
    (width, height) = img.size
    global info
    global info_plus
    
    info = {}
    info_plus = {}
    while param < 3:
        if img.height > 399 and img.width > 399:
            text_reader()
            if len(text) != 0:
                main()
                if param == 1:
                    info_plus = info
                    info = {}
                    param = param + 1
                elif param == 2:
                    
                    param = param + 1
                else:
                    param = param + 1

            else:
                print("Не вдалось розпізнати текст")
                info["Err"] = "Не вдалось розпізнати текст"
                break
        else:
            print("Неможливо розпізнати текст низька роздільна здатність зображення")
            info["Err"] = "Неможливо розпізнати текст низька роздільна здатність зображення"
            break
    if info_plus==info:
        full_info=info
    elif len(info_plus) > len(info):
        full_info={**info, **info_plus}
    elif len(info_plus) < len(info):
        full_info={**info_plus, **info}
    elif len(info_plus) == len(info):
        full_info=info_plus
    else:
        full_info=info


#print(number_data)
def text_reader():
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    global text
    global cyrillic_words
    global latin_words
    global number_data
    global number_with_word
    
    #покращені розпізнавання тексту
    #custom_oem_psm_config  =  r'--oem 3 --psm 6'
    #text = pytesseract.image_to_string(img, lang='rus+eng', config = custom_oem_psm_config)
    if param == 1:
        text = pytesseract.image_to_string(img, lang='rus+eng')
    elif param == 2:
        custom_oem_psm_config  =  r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, lang='rus+eng', config = custom_oem_psm_config)
    else:
        print("done")


    print(text)
    #виділення з тексту кирилиці, латиниці, цифр
    #text = pytesseract.image_to_string(img, lang='rus+eng')
    lat = "a-zA-Z"
    cyr = "а-яА-ЯёЁ"
    cyr_data = "а-яА-ЯёЁ0-9"
    num = "0-9"
    latin_words = re.findall(rf"\b([{lat}]+)\b", text)
    cyrillic_words = re.findall(rf"\b([{cyr}]+)\b", text)
    number_data = re.findall('[0-9]+', text)
    number_with_word = re.findall('[а-яА-ЯёЁ0-9]+', text)
    #print(cyrillic_words)
    print(number_with_word)

def main():
    global name_list
    global surname_list
    global father_list
    global region_identificator_after
    global region_identificator_before
    
    file_name = open('ocr/first_names_rus.txt','r', encoding='utf-8')
    name_list = file_name.read()
    name_list = name_list.upper()
    file_surname = open('ocr/second_names_rus.txt', 'r', encoding='utf-8')
    surname_list = file_surname.read()
    surname_list = surname_list.upper()
    file_father_names = open('ocr/patronymic_rus.txt', 'r', encoding='utf-8')
    father_list = file_father_names.read()
    father_list = father_list.upper()
    
    region_identificator_after = ['КРАЙ', 'КР', 'ОБЛАСТЬ', 'ОБЛ', 'РАЙОН','Р-Н']
    region_identificator_before = ['РЕСПУБЛИКА', 'РЕСП', 'ГОРОД', 'Г', 'ГОР', 'С']
    #print(number_data)
    i = 0
    while len(cyrillic_words) != i:
        if cyrillic_words[i] == 'ВОДИТЕЛЬСКОЕ' and cyrillic_words[i+1] == 'УДОСТОВЕРЕНИЕ':
            info["Doc_Type"]="Водійське посвідчення"
            ocr_driver_licence()
            break
        elif cyrillic_words[i] == 'ПАСПОРТ' or cyrillic_words[i] == 'Паспорт' or cyrillic_words[i] == 'паспорт' or str(cyrillic_words[i]).upper() == 'ФМС' or str(cyrillic_words[i]).upper() == 'МВД' or  (cyrillic_words[i] == 'УДОСТОВЕРЕНИЕ' and cyrillic_words[i+1] == 'ЛИЧНОСТИ') :
            info["Doc_Type"]="Паспорт"
            ocr_passport()
            break
        elif  cyrillic_words[i] != 'ВОДИТЕЛЬСКОЕ'  or cyrillic_words[i] != 'ПАСПОРТ' or cyrillic_words[i] != 'Паспорт' or cyrillic_words[i] != 'паспорт' or cyrillic_words[i] != 'УДОСТОВЕРЕНИЕ'  or str(cyrillic_words[i]).upper() != 'ФМС':
            if i==len(cyrillic_words)-1:
                info["Doc_Type"]="Невідомий"
                find_information()
                break
            else: 
                i=i+1
        else:
            i=i+1
    file_name.close()
    file_surname.close()
    file_father_names.close()
    print(info)


def find_information():
    
    def get_pib():
        # print(type(cyrillic_words))
        i = 0
        while len(cyrillic_words)!=i:
            word = '\n'+ cyrillic_words[i] + '\n'
            word = str(word).upper()
            if word in name_list and str(cyrillic_words[i]).upper()!="ПОЛ":  #пошук по списку імен і прізвищ
                #print("ім'я:" + cyrillic_words[i])
                info["Name"]=cyrillic_words[i]
                #print(cyrillic_words[i])
                i=i+1
                
            elif word in surname_list and word not in father_list:
               # print("Прізвище:" + cyrillic_words[i])
                info["Surname"]=cyrillic_words[i]
                i=i+1
            elif word in father_list:
                #print("По батькові:" + cyrillic_words[i])
                info["Patronymic"]=cyrillic_words[i]
                i = i+1
                '''
            elif (cyrillic_words[i]=='Имя' or cyrillic_words[i]=='ИМЯ') and '\n'+cyrillic_words[i+1] + '\n' not in name_list:
               # print("Ім'я:" + str(cyrillic_words[i+1]+' '+str(cyrillic_words[i+2])))
                info["Name"]=cyrillic_words[i]
                info["Patronymic"]=cyrillic_words[i+1]
                i=i+1
            elif (cyrillic_words[i]=='ФАМИЛИЯ' or cyrillic_words[i]=='Фаммилия' or cyrillic_words[i]=='Фоммилия') and '\n'+cyrillic_words[i+1] + '\n' not in surname_list: 
                #print("Прізвище: " + str(cyrillic_words[i+1]))
                info["Surname"]=cyrillic_words[i]
                i=i+1
                '''
            else: 
                i = i+1
        # print(info)
        get_date_born()
    
    def get_date_born():
        i = 0
        global dates
        dates = 9999
        a = 0
        #print(number_with_word)
       
        while len(number_data)-2!=i:
            if len(number_data[i])==2 and len(number_data[i+1])==2 and len(number_data[i+2])==4:
                num = int(''.join(map(str, number_data[i+2])))
                if num<dates:
                    dates=num
                    a=i
                    i=i+1
                else:
                    i=i+1       
            else:
                i=i+1
        if a>0:
            #print('Можлива дата народження: '+ str(number_data[a])+"."+str(number_data[a+1])+"."+str(number_data[a+2]))
            birthday = str(number_data[a])+"."+str(number_data[a+1])+"."+str(number_data[a+2])
            #print( birthday)
            info["Born"]=birthday
            find_placeborn()
        
        else:
            dates = 9999
            y=0
            i=0
            k=0
            while len(number_with_word)-2!=i:
                mounth = ['Января', 'Февраля', 'Марта', 'Апреля','Мая', 'Июня','Июля', 'Августа','Сентября', 'Октября','Ноября', 'Декабря']    
                if len(number_with_word[i])==2 and str(number_with_word[i+1]).upper() in str(mounth).upper() and len(number_with_word[i+2])==4:
                    num = int(''.join(map(str, number_with_word[i+2])))
                    if dates > num:
                        dates = num
                        k=i
                        i=i+1       
                    else:
                        i=i+1
                else: 
                    i=i+1
            birthday = str(number_with_word[k]) + ' ' +str(number_with_word[k+1])+ ' ' +str(number_with_word[k+2])
            #print('1' + birthday)
            info["Born"]=birthday
            #print(str(number_with_word[k]) + ' ' +str(number_with_word[k+1])+ ' ' +str(number_with_word[k+2]))
            #print(info)
            find_placeborn()

    def find_placeborn():
        global city
        city = ''
        i=0
        #cyrillic_words

        while len(cyrillic_words)-1!=i:
            #if str(cyrillic_words[i]) == "КРАЙ" or str(cyrillic_words[i]) == "КР" or str(cyrillic_words[i]) == "ОБЛ" or str(cyrillic_words[i]) == "ОБЛАСТЬ" or str(cyrillic_words[i]) == "область" or str(cyrillic_words[i]) == "Р-Н" or str(cyrillic_words[i]) == "РАЙОН" or (str(cyrillic_words[i]) == "Р" or str(cyrillic_words[i]) == "Н")  :
            if str(cyrillic_words[i]).upper() in region_identificator_after or  (str(cyrillic_words[i]) == "Р" or str(cyrillic_words[i]) == "Н")  :
                city2 = str(cyrillic_words[i-1]) + ' '+ str(cyrillic_words[i])
                city = city.replace(" ", "", 1)
                #print(city)
                #print(str(city2))
                if city==city2:
                    #print(city)
                    i = i+1
                elif city!=city2:
                    city = city + ' ' +city2
                    # print(city)
                    i = i+1
            elif str(cyrillic_words[i]).upper() in region_identificator_before:
                city2 = str(cyrillic_words[i]) + ' '+ str(cyrillic_words[i+1])
                city = city.replace(" ", "", 1)
                #print(city)
                #print(str(city2))
                if city==city2:
                    #print(city)
                    i=i+1
                elif city!=city2:
                    city = city + ' ' +city2
                    #print(city)
                    i=i+1
            else:
                i=i+1
        #print("Регіон: "+str(city))
        info["Place"] = str(city)
        #print(info)


    get_pib()  


def ocr_driver_licence():
    def get_pib_from_driver_licence():
        i = 0
        pib = ''
        while len(cyrillic_words)!=i:
            word = '\n'+cyrillic_words[i] + '\n'
            word = str(word).upper()
            if word in name_list:  #пошук по списку імен і прізвищ
                pib = "ім'я: " + str(cyrillic_words[i])
                info["Name"]=cyrillic_words[i]
                i = i+1
            elif word in surname_list and word not in father_list:

                # print(cyrillic_words[i])
                pib = pib + " Прізвище: " + cyrillic_words[i]
                info["Surname"]=cyrillic_words[i]
                i=i+1
            elif word in father_list:
                pib = pib + " По батькові: " + cyrillic_words[i]
                info["Patronymic"]=cyrillic_words[i]
                i = i+1
                '''    
            elif word not in surname_list and str(cyrillic_words[i]).upper() in region_identificator_after :
                pib = pib + " Прізвище: " + cyrillic_words[i-4] 
                info["Surname"]=cyrillic_words[i-4]                
                i=i+1
                break
                
            elif word not in surname_list and str(cyrillic_words[i]).upper() in region_identificator_before:
                pib = pib + " Прізвище: " + cyrillic_words[i-3]
                info["Surname"]=cyrillic_words[i-3]
                i=i+1
                break
                '''
            else:
                i = i+1
        
        #print(pib)
        find_born()
            



    def find_region():
        global city
        city = ''
        i = 0

        #cyrillic_words
        while len(cyrillic_words)!=i:
            if str(cyrillic_words[i]).upper() in region_identificator_after :
                city2 = str(cyrillic_words[i-1]) + ' '+ str(cyrillic_words[i])
                city = city.replace(" ", "", 1)
                #print(city)
                #print(str(city2))
                if city == city2:
                    #print(city)
                    i=i+1
                elif city!=city2:
                    city = city + ' ' +city2
                    #print(city)
                    i=i+1
            elif str(cyrillic_words[i]).upper() in region_identificator_before:
                city2 = str(cyrillic_words[i]) + ' '+ str(cyrillic_words[i+1])
                city = city.replace(" ", "", 1)
                #print(city)
                #print(str(city2))
                if city==city2:
                    #print(city)
                    i=i+1
                elif city!=city2:
                    city = city + ' ' +city2
                    #print(city)
                    i=i+1
            else:
                i=i+1
        info["Place"]=str(city)
        #print("Регіон: "+str(city))
        find_identificator_drive_licence()
        
        
    def find_identificator_drive_licence():  #пошук номера посвідчення та номера ГИБДД яке видало 
        gbdd = "ГИБДД"
        if gbdd in number_with_word:
            indexofgbdd = number_with_word.index(gbdd)
            info["GBDD_NUMBER"]=str(number_with_word[indexofgbdd+1])
            i=0
            while len(number_data)!=i:
                if len(number_data[i])==10:
                    number_licence = str(number_data[i])
                    info["Licence_number"]=str(number_licence)
                    i=i+1       
                elif len(number_data[i])==6:
                    number_licence = str(number_data[i-2]) + str(number_data[i-1]) + str(number_data[i])
                    info["Licence_number"]=str(number_licence)

                    i=i+1  
                else:
                    i=i+1
            #print("Пошук ідентифікатора")
        else:
            print("Помилка 1")
        #print(info)

    def find_born():
        i=0
        global dates
        dates = 9999
        b=0
        x=0
        while len(number_data)-2!=i:
            if len(number_data[i])==2 and len(number_data[i+1])==2 and len(number_data[i+2])==4:
                num = int(''.join(map(str, number_data[i+2])))
                if num<dates:
                    dates=num
                    a=i
                    i=i+1
                elif num>dates:
                    dates = num
                    d=dates
                    b=i
                    i=i+1
                    if x==0:
                        #print('Дійсне з '+ str(number_data[b])+"."+str(number_data[b+1])+"."+str(number_data[b+2]))
                        valid_w = str(number_data[b])+"."+str(number_data[b+1])+"."+str(number_data[b+2])
                        info["Valid_with"] = valid_w
                        x=x+1
                    elif x==1:
                        #print('Дійсне до: '+ str(number_data[b])+"."+str(number_data[b+1])+"."+str(number_data[b+2]))  
                        valid_u = str(number_data[b])+"."+str(number_data[b+1])+"."+str(number_data[b+2])
                        info["valid_until"] = valid_u

                else:
                    i=i+1       
            else:
                i=i+1
        #print('Можлива дата народження: '+ str(number_data[a])+"."+str(number_data[a+1])+"."+str(number_data[a+2]))
        birthday = str(number_data[a])+"."+str(number_data[a+1])+"."+str(number_data[a+2])
        info["Born"]=birthday
        #print(info)
        find_region()
    get_pib_from_driver_licence()
    



def ocr_passport():
    
    def find_passportborn():
        i=0
        global dates
        dates = 9999
        b=0
        x=0
        a=0
        while len(number_data)-2!=i:
            if len(number_data[i])==2 and len(number_data[i+1])==2 and len(number_data[i+2])==4:
                num = int(''.join(map(str, number_data[i+2])))
                if num<dates:
                    dates=num
                    a=i+1
                    i=i+1
                else:
                    i=i+1      
            else:
                i=i+1
        if a>0:    
            #print('Можлива дата народження: '+ str(number_data[a])+"."+str(number_data[a+1])+"."+str(number_data[a+2]))  
            birthday = str(number_data[a-1])+"."+str(number_data[a])+"."+str(number_data[a+1])
            info["Born"]=birthday
            find_passportplaceborn()
        else:
            find_passportplaceborn()


    def find_passportplaceborn():
        global city
        city = ''
        i=0
        #cyrillic_words
        while len(cyrillic_words)!=i:
            if str(cyrillic_words[i]).upper() in region_identificator_after:
                city2 = str(cyrillic_words[i-1]) + ' '+ str(cyrillic_words[i])
                city = city.replace(" ", "", 1)
                #print(city)
                #print(str(city2))
                if city==city2:
                    #print(city)
                    i=i+1
                elif city!=city2:
                    city = city + ' ' +city2
                    #print(city)
                    i=i+1
            elif str(cyrillic_words[i]).upper() in region_identificator_before:
                city2 = str(cyrillic_words[i]) + ' '+ str(cyrillic_words[i+1])
                city = city.replace(" ", "", 1)
                #print(city)
                #print(str(city2))
                if city==city2:
                    #print(city)
                    i=i+1
                elif city!=city2:
                    city = city + ' ' +city2
                    #print(city)
                    i=i+1
            else:
                i=i+1
        #print("Регіон: "+str(city))
        info["Place"]=str(city)
        get_fms_number()

    def get_fms_number():
        i=0
        number_with_word = re.findall('[а-яА-ЯёЁ0-9]+', text)
        #print(number_with_word)
        while len(number_with_word)!=i:
            if (str(number_with_word[i]) == "ФМС" or str(number_with_word[i]) == "МВД") and len(number_with_word[i+1])==5 :
                id_fms = number_with_word[i+1]
                #print("Номер підрозділу, що видав: " + str(number_with_word[i+1]))
                info["FMS_number"]=str(number_with_word[i+1])
                break
            elif len(number_with_word[i])==3 and len(number_with_word[i+1])==3 and str(number_with_word[i]).isdigit():
                #print("Номер підрозділу, що видав: " + str(number_with_word[i]) + '-'+ str(number_with_word[i+1]))
                info["FMS_number"]=str(number_with_word[i]) + '-'+str(number_with_word[i+1])
                break
            else:
                i=i+1
        #print(info)
        get_passport_number()

    def get_passport_number():
        i=0
        while len(number_data)!=i:
            if len(number_data[i])==9:
                #print('Номер паспорта:' + str(number_data[i]))
                i=i+1
                info["Pasport_number"]=str(number_with_word[i])
            elif len(number_data[i])==7 and len(number_data[i-1])==2:
                pasport_n = str(number_data[i-1])+" "+str(number_data[i])
                #print('Номер паспорта:'+str(number_data[i-1])+" "+str(number_data[i]))
                info["Pasport_number"]=pasport_n
                i=i+1
            elif i+1<len(number_data) and len(number_data[i])==2 and len(number_data[i+1])==2 and len(number_data[i+2])==6:
                pasport_n = str(number_data[i])+" "+str(number_data[i+1])+" "+str(number_data[i+2])
                #print('Номер паспорта: '+ str(number_data[i])+" "+str(number_data[i+1])+" "+str(number_data[i+2]))
                info["Pasport_number"]=pasport_n
                i=i+1
            else:
                i=i+1
        #print(info)
        
    def get_pib_from_passport():
        #print(cyrillic_words)
        i=0
        while len(cyrillic_words)!=i:
            word = '\n'+cyrillic_words[i] + '\n'
            if word in name_list and len(cyrillic_words[i])>2:  #пошук по списку імен і прізвищ
                #print("ім'я:" + cyrillic_words[i])
                info["Name"]=cyrillic_words[i]
                i=i+1
            elif word in surname_list and word not in father_list:
                #print("Прізвище:" + cyrillic_words[i])
                info["Surname"]=cyrillic_words[i]
                i=i+1
            elif word in father_list:
                #print("По батькові:" + cyrillic_words[i])
                info["Patronymic"]=cyrillic_words[i]
                i=i+1
                '''
            elif (cyrillic_words[i]=='Имя' or cyrillic_words[i]=='ИМЯ') and '\n'+cyrillic_words[i+1] + '\n' not in name_list:
                #print("Ім'я:" + str(cyrillic_words[i+1]+' '+str(cyrillic_words[i+2])))
                info["Name"]=cyrillic_words[i+1]
                info["Patronymic"]=cyrillic_words[i+2]
                i=i+1
            elif (cyrillic_words[i]=='ФАММИЛИЯ' or cyrillic_words[i]=='Фаммилия' or cyrillic_words[i]=='Фоммилия') and '\n'+cyrillic_words[i+1] + '\n' not in surname_list: 
                #print("Прізвище: " + str(cyrillic_words[i+1]))
                info["Surname"]=cyrillic_words[i+1] 
                i=i+1
                '''
            else: 
                i=i+1
        find_passportborn()
    get_pib_from_passport()



    
'''
#запис у файл
with open("passport_data.txt", 'a') as f:
    f.write(str(latin_words)+'\n')
    f.write(str(cyrillic_words)+'\n')
    f.write(str(number_data)+'\n')
'''