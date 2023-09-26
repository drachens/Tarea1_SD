import grpc
import cache_service_pb2
import cache_service_pb2_grpc
import json
import time
import random
import matplotlib.pyplot as plt
from pymemcache.client import base
import os

def clear():
    if os.name == 'posix':  # Para sistemas Unix/Linux/Mac
        os.system('clear')
    elif os.name == 'nt':  # Para sistemas Windows
        os.system('cls')

def find_car_by_id(target_id, file_path="./cars.json"):
    with open(file_path, 'r') as f:
        f.seek(0, 2)
        total_size = f.tell()     
        low = 0
        high = total_size     
        while low <= high:
            mid = (low + high) // 2
            f.seek(mid)
            while f.read(1) != "{":
                f.seek(f.tell() - 3)
            obj_str = "{"  
            while True:
                char = f.read(1)
                obj_str += char
                if char == "}":
                    break  
            obj = json.loads(obj_str)  
            if obj["id"] == target_id:
                return obj
            elif obj["id"] < target_id:
                low = mid + 1
            else:
                high = mid - 1

def graficar(x,y,titulo="Grafico",etiqueta_x="Consultas",etiqueta_y="Tiempo respuesta"):
    plt.bar(x,y)
    plt.title(titulo)
    plt.xlabel(etiqueta_x)
    plt.ylabel(etiqueta_y)
    plt.ylim(0,2)
    plt.grid(True)

class MemcachedClient:
    def __init__(self, host="localhost", port=11211):
        self.host = host
        self.port = port
        self.client = base.Client((host,port))
    
    def put(self, key, value, expiration=0):
        key_str = str(key)
        if isinstance(value,dict):
            value_str = str(value)
        else:
            value_str = value
        return self.client.set(key_str, value_str, expiration, noreply=False)
    
    def get(self, key):
        key_str = str(key)
        response = self.client.get(key_str, default=False)
        if response: #Si está en cache
            isCached = 1
            isNotCached = 0
            return response, isCached, isNotCached
        else:
            isCached = 0
            isNotCached = 1
            value = find_car_by_id(int(key_str)) #Buscar en JSON
            if value:
                self.client.set(key_str,value)
                return value, isCached, isNotCached
            else:
                print("Key not exist.")
                return None
            
    def remove(self, key):
        key_str = str(key)
        response = self.client.delete(key_str, noreply=False)
        return response

    
class CacheClient: #Busqueda usando cache casero
    def __init__(self, host="localhost", port=50051):
        self.channel = grpc.insecure_channel(f"{host}:{port}")
        self.stub = cache_service_pb2_grpc.CacheServiceStub(self.channel)

    def put(self, key, value):
        response = self.stub.Put(cache_service_pb2.CacheItem(key=key, value=value))
        print(response.message)

    def get(self, key):
        response = self.stub.Get(cache_service_pb2.Key(key=key))
        if response.value:  # Si existe en cache
            isCached = 1
            isNotCached = 0
            value = response.value.replace("'","\"") #Cambiar comillas simples por dobles
            value = json.loads(value) #Convertir en diccionario
            return value, isCached, isNotCached #Retorna objeto, HitRate, Miss
        else: #Si no existe se realizará la busqueda en JSON
            value = find_car_by_id(int(key))
            isCached = 0
            isNotCached = 1
            if value:
                self.stub.Put(cache_service_pb2.CacheItem(key=key, value=str(value)))
                return value, isCached, isNotCached #Retorna objeto y tiempo de demora de busqueda
            else:
                print("Key not exist.")
                return None
            

    def remove(self, key):
        response = self.stub.Remove(cache_service_pb2.Key(key=key))
        if response.success == True:
            return True
        else:
            return False
        #print("[CACHECASERO]",response.message, "Llave eliminada: ",key)
    

    
if __name__ == "__main__":
    consultas = 100
    json_metrics = {}
    while True:
        count = 0
        count_2 = 0
        print("\nElige una operacion:")
        print("1. Usar JSON")
        print("2. Usar Cache Casero")
        print("3. Usar MEMEMCACHE")
        print("4. Borrar Caches")
        print("5. Graficar tiempos")
        print("6. Comparativas hit rate y miss rate")
        print("7. Exit")
        choice = input("Elige una opcion: ")
        if choice == "1": #JSON
            clear()
            key = "Json"
            while True:
                print("\n[JSON]Elige una operacion:")
                print("1. Simular consultas con una distribución normal")
                print("2. Simular consultas de frecuencia constante 1")
                print("3. Retroceder")
                opcion = input("Ingresa una opcion: ")
                if opcion == "1": #[CaseCasero] Dis. Norm.
                    start_time = time.time()
                    num = int(random.gauss(49.5,16.5)) #Dist. Normal con media 50 y desviacion 20
                    num_ajus = int(max(0,min(99,num))) #Ajustar numero dentro del rango 0-99 
                    for i in range(consultas):
                        find_car_by_id(int(num_ajus))
                    end_time = time.time() - start_time
                    json_aux = {"time":end_time, "consultas":consultas, "hit_rate":0,"miss_rate":100}
                    json_metrics[key] = json_aux

                elif opcion == "2":
                    start_time = time.time()
                    for i in range(consultas):
                        find_car_by_id(int(i))
                    end_time = time.time() - start_time
                    json_aux = {"time":end_time, "consultas":consultas, "hit_rate":0,"miss_rate":100}
                    json_metrics[key] = json_aux
                elif opcion == "3":
                    break
                else:
                    print("\nIngrese una opcion válida")

        elif choice == "2": #Cache Casero
            clear()
            key = "CacheCasero"
            client = CacheClient()
            while True:
                print("\n[CACHECASERO]Elige una operacion")
                print("1. Simular consultas con una distribución normal")
                print("2. Simular consultas de frecuencia constante 1")
                print("3. Retroceder")
                opcion = input("Ingresa una opcion: ")
                if opcion == "1": #[CaseCasero] Dis. Norm.
                    hit = miss = 0
                    start_time = time.time()
                    for i in range(consultas):
                        num = int(random.gauss(49.5,16.5)) #Dist. Normal con media 50 y desviacion 20
                        num_ajus = int(max(0,min(99,num))) #Ajustar numero dentro del rango 0-99
                        value, isCached, isNotCached = client.get(str(num_ajus)) #Guardar datos 
                        hit = hit + isCached
                        miss = miss + isNotCached
                    end_time = time.time() - start_time
                    hit_rate = (hit/(hit + miss))*100 #Hit rate
                    miss_rate = (miss/(hit + miss))*100 #Miss rate
                    json_aux = {"time":end_time, "consultas":consultas, "hit_rate":hit_rate,"miss_rate":miss_rate}
                    json_metrics[key] = json_aux
                elif opcion == "2": #[CacheCasero] frecuencia 1
                    hit = miss = 0
                    start_time = time.time()
                    for i in range(consultas):
                        value, isCached, isNotCached = client.get(str(i))
                        hit = hit + isCached
                        miss = miss + isNotCached
                    end_time = time.time() - start_time
                    hit_rate = (hit/(hit + miss))*100
                    miss_rate = (miss/(hit + miss))*100
                    json_aux = {"time":end_time, "consultas":consultas, "hit_rate":hit_rate,"miss_rate":miss_rate}
                    json_metrics[key] = json_aux
                elif opcion == "3":
                    break
                else:
                    print("\nIngrese una opcion válida")

        elif choice == "3":
            clear()
            key = "MemCached"
            client = MemcachedClient()
            while True:
                print("\n[MEMCACHED] Elige una operacion")
                print("1. Simular consultas con una distribución normal")
                print("2. Simular consultas de frecuencia constante 1")
                print("3. Retroceder")
                opcion = input("Ingresa una opcion: ")
                if opcion == "1": #[MEMCACHED] Dist. Norm.
                    hit = miss = 0
                    start_time = time.time()
                    for i in range(consultas):
                        num = int(random.gauss(49.5,16.5)) #Dist. Normal con media 50 y desviacion 20
                        num_ajus = int(max(0,min(99,num))) #Ajustar numero dentro del rango 0-99
                        value, isCached, isNotCached = client.get(str(num_ajus)) #Guardar datos
                        hit = hit + isCached
                        miss = miss + isNotCached
                    end_time = time.time() - start_time
                    hit_rate = (hit/(hit + miss))*100 #Calcular hit rate
                    miss_rate = (miss/(hit + miss))*100 #Calcular miss rate
                    json_aux = {"time":end_time, "consultas":consultas, "hit_rate":hit_rate,"miss_rate":miss_rate}
                    json_metrics[key] = json_aux
                elif opcion == "2":#[MEMCACHED] Frecuencia 1
                    hit = miss = 0
                    start_time = time.time()
                    for i in range(consultas):
                        value, isCached, isNotCached = client.get(str(i))
                        hit = hit + isCached
                        miss = miss + isNotCached
                    end_time = time.time() - start_time
                    hit_rate = (hit/(hit + miss))*100 #Calcular hit rate
                    miss_rate = (miss/(hit + miss))*100 #Calcular miss rate
                    json_aux = {"time":end_time, "consultas":consultas, "hit_rate":hit_rate,"miss_rate":miss_rate}
                    json_metrics[key] = json_aux
                elif opcion == "3":
                    break
                else:
                    print("\nIngrese una opcion válida")

        elif choice == "4":
            client_Mem = MemcachedClient()
            client_casero = CacheClient()
            for i in range(100):
                if client_Mem.remove(str(i)):
                    print("[MEMCACHED] Key removed: ",str(i))

                if client_casero.remove(str(i)):
                    print("[CACHECASERO] Key removed: ", str(i))

        elif choice == "5":
            data = json_metrics
            x = ["JSON","CacheCasero","MemCached"]
            y = [data["Json"]["time"],data["CacheCasero"]["time"],data["MemCached"]["time"]]
            plt.figure(figsize=(10,5))
            graficar(x,y,"Grafico Comparativas de tiempo","Sistema utilizado","Tiempo")
            for i, valor in enumerate(y):
                plt.text(x[i], round(valor,5), str(round(valor,5)), ha='center', va='bottom')
            plt.show()

        elif choice == "6":
            clear()
            print("\n[CacheCasero] Hit rate y Miss rate:")
            print("HIT = ", json_metrics["CacheCasero"]["hit_rate"]," MISS = ",json_metrics["CacheCasero"]["miss_rate"])
            print("\n[MemCached] Hit rate y Miss rate:")
            print("HIT = ",json_metrics["MemCached"]["hit_rate"]," MISS = ",json_metrics["MemCached"]["miss_rate"])
        
        elif choice == "7":
            clear()
            print("\n Adios!")
            break
        
        else:
            print("\nIngrese una opcion valida.")