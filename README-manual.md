# Workshop - OCI Generative AI para procesamiento de recetas y abstraccion de modelos con LiteLLM

> Guia operativa para participantes. Punto de partida: cada participante cuenta con una VM en Oracle Cloud Infrastructure (OCI), descargara el repositorio del workshop desde GitHub y ejecutara los proyectos dentro de la VM.

## 0. Objetivo del workshop

Al finalizar el laboratorio, el participante habra construido y validado dos proyectos independientes:

| Proyecto | Proposito | Enfoque |
|---|---|---|
| `oci-genai-oci-only` | Construir el pipeline base usando OCI Generative AI directamente | Responses API, Vision, Structured Output, validacion externa con CIMA, RAG con politicas y decision de Farmacia |
| `oci-genai-litellm` | Incorporar LiteLLM como gateway de modelos sin mezclarlo con el proyecto base | Seleccion dinamica de modelo, LiteLLM Proxy, API para Postman, comparacion Gemini vs Grok |

La idea pedagogica es separar dos momentos:

1. **Construir la solucion con OCI Generative AI.**
2. **Desacoplar el consumo de modelos mediante LiteLLM.**

Luego, en un siguiente modulo, LangSmith podra usarse para observar y comparar las ejecuciones.

---

## 1. Mapeo de arquitectura

La arquitectura agnostica a nube que se usa como referencia contiene componentes como usuario/aplicacion cliente, gestor de LLMs, proveedores, proxy de LLM, agentes, MCP, RAG, observabilidad y gobierno. En este workshop se implementa un subconjunto practico:

| Bloque de la arquitectura agnostica | Implementacion en el workshop |
|---|---|
| Usuario / aplicacion cliente | Python CLI y Postman |
| LLM Providers | Modelos disponibles en OCI Generative AI |
| LLM Proxy | LiteLLM Proxy en el Proyecto 2 |
| RAG | OCI Vector Store + File Search con politicas institucionales |
| Herramientas externas | CIMA AEMPS como API externa de validacion farmacologica |
| Gobierno y seguridad | `.env`, no secretos en codigo, separacion de proyectos, control de API key, no publicar `.env` |
| Observabilidad | Preparado para LangSmith en el siguiente modulo |

Este workshop **no cubre MCP ni agentes autonomos** dentro del hands-on principal. Esos conceptos se dejan como extension arquitectonica.

---

## 2. Configuracion previa en la consola de OCI

> Nota: en este workshop la consola cloud requerida es **OCI Console**, no AWS Console. AWS Bedrock puede ser parte de una arquitectura agnostica futura, pero los laboratorios actuales usan OCI Generative AI, OCI Vector Store, una VM en OCI y una API externa publica (CIMA).

Antes de abrir la VM y ejecutar codigo, el instructor debe preparar o verificar los siguientes recursos en OCI. Esta seccion debe completarse **una sola vez por tenancy/compartment** o por cada grupo de participantes, segun el modelo de entrega del workshop.

### 2.1 Region y compartment de trabajo

1. Ingresar a **OCI Console**.
2. Seleccionar una region donde esten disponibles los modelos que se usaran en el laboratorio. La guia usa por defecto:

```text
us-chicago-1
```

3. Crear o seleccionar un compartment para el laboratorio, por ejemplo:

```text
workshop-genai
```

4. Anotar:

```text
OCI_GENAI_REGION=us-chicago-1
<COMPARTMENT_NAME>=workshop-genai
```

La disponibilidad de modelos varia por region. Antes del workshop, validar que los modelos declarados en `.env` existan en la region elegida.

### 2.2 Permisos IAM minimos para el workshop

Si el participante no pertenece al grupo `Administrators`, solicitar a un administrador que asigne permisos al grupo de trabajo. Para un entorno de laboratorio controlado, una politica amplia y simple es:

```text
allow group <grupo-workshop> to manage generative-ai-family in compartment <compartment-workshop>
```

Esta politica permite crear y administrar recursos de OCI Generative AI en el compartment del workshop, incluyendo proyectos, API keys y vector stores.

Para permitir llamadas usando **OCI Generative AI API Key**, agregar tambien una politica de uso para API keys. En un sandbox, puede usarse una regla amplia por compartment:

```text
allow any-user to manage generative-ai-family in compartment <compartment-workshop>
where ALL {request.principal.type='generativeaiapikey'}
```

En un entorno mas restringido, usar la OCID especifica del API key:

```text
allow any-user to manage generative-ai-family in compartment <compartment-workshop>
where ALL {request.principal.type='generativeaiapikey', request.principal.id='<api-key-ocid>'}
```

> Recomendacion: para el workshop se usan API keys por simplicidad. Para produccion, preferir autenticacion IAM cuando la aplicacion corre dentro de OCI.

### 2.3 Crear el proyecto de OCI Generative AI

1. En OCI Console, abrir **Analytics & AI**.
2. Ir a **Generative AI**.
3. Seleccionar **Projects**.
4. Click en **Create project**.
5. Usar un nombre reconocible, por ejemplo:

```text
genai-recipe-workshop
```

6. Seleccionar el compartment del workshop.
7. Crear el proyecto.
8. Abrir el proyecto y copiar su OCID.
9. Guardarlo para el archivo `.env`:

```dotenv
OCI_GENAI_PROJECT_ID=<ocid1.generativeaiproject...>
```


- **Response retention** y **Conversation retention**: definen cuanto tiempo se retienen respuestas o conversaciones administradas por el servicio. Para el laboratorio se pueden dejar los valores por defecto del tenancy.
- **Short-term memory compaction**: compacta contexto en conversaciones largas. 
- **Long-term memory**: memoria persistente. Se deja deshabilitada para separar claramente memoria de RAG.


> En este laboratorio primero trabajamos con llamadas controladas, artefactos JSON y RAG explicito. Memoria y compaction son capacidades avanzadas que se pueden introducir despues.

### 2.4 Crear el API Key de OCI Generative AI

1. En **Generative AI**, ir a **API keys**.
2. Click en **Create API key**.
3. Asignar un nombre, por ejemplo:

```text
recipe-workshop-api-key
```

4. Seleccionar el compartment del workshop.
5. Crear la clave.
6. Copiar el valor secreto del API key y guardarlo temporalmente en un gestor seguro.
7. Copiar tambien la OCID del API key si se usara una politica IAM restringida por clave.
8. En `.env`, configurar:

```dotenv
OCI_GENAI_API_KEY=<valor-del-api-key>
```

Nunca publicar esta clave en GitHub. Si se comparte accidentalmente, rotarla inmediatamente.

### 2.5 Verificar modelos y alias del laboratorio

En la consola de Generative AI, validar que los modelos elegidos esten disponibles en la region. En este workshop se usan alias logicos:

```dotenv
OCI_GENAI_DEFAULT_MODEL=gemini
OCI_GENAI_MODELS_JSON={"gemini":"google.gemini-2.5-flash","grok":"xai.grok-4.3"}
```

Si en el tenancy se usa otro identificador de modelo, cambiar solo el `.env`, no el codigo.

### 2.6 Crear el Vector Store para RAG

1. En **Generative AI**, ir a **Vector stores**.
2. Click en **Create vector store**.
3. Nombre sugerido:

```text
recipe-policy-vector-store
```

4. Seleccionar el compartment del workshop.
5. Data source type: **Unstructured data**.
6. Crear el vector store.
7. Copiar el ID/OCID mostrado por la consola.
8. Configurar en `.env`:

```dotenv
OCI_GENAI_VECTOR_STORE_ID=<vector-store-id>
```

En este workshop los archivos de politicas se cargan desde Python con `06_upload_knowledge.py`. Por eso no es obligatorio configurar un conector de Object Storage. Si se desea sincronizar grandes volumenes de documentos desde Object Storage, se requeriran permisos adicionales para el conector.

### 2.7 Crear la VM de laboratorio en OCI

La VM puede ser creada por el instructor para cada participante o por los participantes siguiendo estos pasos.

1. En OCI Console, ir a **Compute > Instances**.
2. Click en **Create instance**.
3. Nombre sugerido:

```text
vm-genai-workshop-<participante>
```

4. Seleccionar el compartment del workshop.
5. Imagen recomendada: Oracle Linux
6. Shape sugerido para laboratorio:

```text
2 OCPU / 16 GB RAM / 100 GB boot volume
```

7. Networking:
   - Usar una VCN y subnet publica o una red privada con bastion/VPN.
   - Asignar public IP si los participantes se conectaran directamente.
   - Habilitar salida a internet para instalar paquetes y consultar CIMA.
8. Acceso remoto:
   - Windows: habilitar acceso RDP solo desde IPs autorizadas.
   - Linux: agregar SSH public key y permitir SSH solo desde IPs autorizadas.
9. No abrir publicamente los puertos en un ambiente productivo:

```text
4000  LiteLLM Proxy
8000  Recipe API
```

Estos puertos deben quedar en `localhost` dentro de la VM. Si se requiere acceso desde fuera, usar tuneles controlados, bastion, VPN o reglas restringidas por IP.

### 2.8 Validacion previa del instructor

Antes del workshop, debemos validar:

```text
1. La VM puede conectarse a internet.
2. Python, Git, VS Code y Postman estan instalados.
3. El API key de OCI Generative AI funciona.
4. El proyecto OCI Generative AI existe y su OCID esta disponible.
5. El Vector Store existe y su ID esta disponible.
6. La region contiene los modelos definidos en OCI_GENAI_MODELS_JSON.
7. CIMA responde desde la VM.
8. Los puertos 4000 y 8000 no estan expuestos publicamente.
```

Referencias oficiales utiles:

- OCI OpenAI-compatible endpoint: https://docs.oracle.com/en-us/iaas/Content/generative-ai/openai-compatible-api.htm
- Uso de proyectos en OCI Generative AI: https://docs.oracle.com/en-us/iaas/Content/generative-ai/use-project.htm
- Crear proyecto: https://docs.oracle.com/en-us/iaas/Content/generative-ai/create-project.htm
- Crear API key: https://docs.oracle.com/en-us/iaas/Content/generative-ai/create-api-key.htm
- Permisos IAM para OCI Generative AI: https://docs.oracle.com/en-us/iaas/Content/generative-ai/iam-policies.htm
- Crear Vector Store: https://docs.oracle.com/en-us/iaas/Content/generative-ai/create-vector-store.htm
- API de archivos de Vector Store: https://docs.oracle.com/en-us/iaas/Content/generative-ai/vector-store-files.htm
- Crear instancia de Compute: https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/launchinginstance.htm


---

## 3. Preparacion de la VM para el workshop

> Esta seccion se ejecuta **dentro de la VM creada en OCI**. El objetivo es dejar lista la estacion de trabajo antes de clonar el repositorio y ejecutar los laboratorios.

### 3.1 Validar sistema operativo y conectividad

En una VM Windows Server, abrir PowerShell y validar:

```powershell
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsArchitecture
Test-NetConnection github.com -Port 443
Test-NetConnection pypi.org -Port 443
Test-NetConnection cima.aemps.es -Port 443
```

En Oracle Linux o Ubuntu:

```bash
cat /etc/os-release
curl -I https://github.com
curl -I https://pypi.org
curl -I https://cima.aemps.es
```

La VM necesita salida HTTPS a Internet para descargar dependencias, clonar GitHub, consumir OCI Generative AI y consultar CIMA.

### 3.2 Instalar Git

#### Windows Server

Opcion recomendada para el workshop: instalar **Git for Windows** desde su instalador oficial o mediante `winget` si esta disponible:

```powershell
winget install --id Git.Git -e
```

Cerrar y abrir PowerShell despues de la instalacion. Validar:

```powershell
git --version
```

Resultado esperado:

```text
git version 2.x.x.windows.x
```

#### Oracle Linux

```bash
sudo dnf install -y git
git --version
```

#### Ubuntu

```bash
sudo apt update
sudo apt install -y git
git --version
```

> `git config --global user.name` y `user.email` no son necesarios para clonar. Solo configurarlos si el participante realizara commits.

### 3.3 Instalar Python

El laboratorio fue validado con **Python 3.12**. Se recomienda mantener la misma version para reducir diferencias entre participantes.

#### Windows Server

Si `winget` esta disponible:

```powershell
winget install --id Python.Python.3.12 -e
```

Durante una instalacion grafica de Python, marcar **Add python.exe to PATH**.

Cerrar y volver a abrir PowerShell. Validar:

```powershell
python --version
python -m pip --version
where.exe python
```

Resultado esperado:

```text
Python 3.12.x
```

#### Oracle Linux

Primero validar:

```bash
python3 --version
```

Si no esta instalado:

```bash
sudo dnf install -y python3 python3-pip
python3 --version
pip3 --version
```

#### Ubuntu

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
python3 --version
```

### 3.4 Instalar VS Code

VS Code no es requerido por los scripts, pero facilita seguir el workshop, revisar JSON y editar `.env`.

En Windows, si `winget` esta disponible:

```powershell
winget install --id Microsoft.VisualStudioCode -e
```

Extensiones recomendadas:

```text
Python - Microsoft
Pylance - Microsoft
```

### 3.5 Instalar Postman

Postman se utiliza en el Proyecto 2 para consumir `Recipe API` por HTTP.

En Windows, si `winget` esta disponible:

```powershell
winget install --id Postman.Postman -e
```

Si los participantes no pueden instalar Postman, las mismas APIs pueden probarse con PowerShell `Invoke-RestMethod` o `curl`.

### 3.6 Instalar utilidades opcionales

En Windows ya se dispone normalmente de `curl.exe`. Validar:

```powershell
curl.exe --version
```

En Linux:

```bash
sudo dnf install -y curl wget unzip
```


### 3.7 Validacion de herramientas base

Antes de continuar, ejecutar:

```powershell
python --version
git --version
```

Checklist:

```text
Python 3.12 disponible   [ ]
Git disponible           [ ]
VS Code instalado        [ ]
Postman instalado        [ ]
Salida HTTPS a Internet  [ ]
```

---

## 4. Instalacion y configuracion de OCI CLI

> OCI CLI no reemplaza la API OpenAI-compatible utilizada por el codigo. Se instala para validar identidad, region, permisos y acceso al tenancy desde la VM.

### 4.1 Instalar OCI CLI en Windows

La forma mas simple para un workshop es usar el instalador oficial de OCI CLI para Windows. Alternativamente, con Python disponible:

```powershell
python -m pip install --upgrade oci-cli
```

Validar:

```powershell
oci --version
```

Si `oci` no se reconoce inmediatamente, cerrar y abrir PowerShell o revisar la carpeta `Scripts` de Python en `PATH`.

### 4.2 Instalar OCI CLI en Linux

Oracle mantiene un instalador oficial. Ejecutar:

```bash
bash -c "$(curl -L https://raw.githubusercontent.com/oracle/oci-cli/master/scripts/install/install.sh)"
```

Aceptar las rutas por defecto para el workshop. Luego abrir una nueva shell o ejecutar:

```bash
exec -l $SHELL
oci --version
```

### 4.3 Configurar OCI CLI con API Signing Key

Ejecutar:

```powershell
oci setup config
```

En Linux es el mismo comando:

```bash
oci setup config
```

El asistente solicitara:

```text
Tenancy OCID
User OCID
Region
Ruta de configuracion
Generacion o ubicacion de API signing key
```

Archivo esperado:

```text
Windows: %USERPROFILE%\.oci\config
Linux:   ~/.oci/config
```

Ejemplo conceptual:

```ini
[DEFAULT]
user=ocid1.user.oc1..example
tenancy=ocid1.tenancy.oc1..example
fingerprint=aa:bb:cc:dd:...
region=us-chicago-1
key_file=C:\Users\opc\.oci\oci_api_key.pem
```

> `OCI CLI API signing key` y `OCI Generative AI API Key` son credenciales diferentes. La primera autentica OCI CLI/SDK; la segunda se utiliza en este workshop con el endpoint OpenAI-compatible de OCI Generative AI.

### 4.4 Registrar la API signing public key en OCI Console

Si `oci setup config` genero un nuevo par de claves:

1. Abrir OCI Console.
2. Ir a **Profile > My profile**.
3. Abrir **API keys**.
4. Seleccionar **Add API key**.
5. Elegir **Paste public key**.
6. Pegar el contenido de la clave publica generada por `oci setup config`.

En Windows, la clave suele quedar bajo:

```text
%USERPROFILE%\.oci\
```

En Linux:

```bash
ls -la ~/.oci
```

Nunca publicar la clave privada ni el archivo `~/.oci/config` en GitHub.

### 4.5 Validar autenticacion OCI CLI

Ejecutar:

```powershell
oci iam region list
```

Tambien puede verificarse la suscripcion de regiones:

```powershell
oci iam region-subscription list
```

En Linux son los mismos comandos.

Si la respuesta es satisfactoria, la VM puede autenticarse contra OCI con la identidad configurada.

### 4.6 Validar region del workshop

El `.env` del workshop usara, por ejemplo:

```dotenv
OCI_GENAI_REGION=us-chicago-1
```

Validar que la region configurada en OCI CLI sea consistente con la region seleccionada en OCI Console.

En PowerShell:

```powershell
Get-Content $HOME\.oci\config
```

En Linux:

```bash
grep '^region=' ~/.oci/config
```

### 4.7 Seguridad de credenciales

Para el workshop:

- No subir `.env` a GitHub.
- No subir `.oci/config` a GitHub.
- No subir claves privadas `.pem`.
- No escribir API keys directamente en Python o YAML.
- Si una clave se publica accidentalmente, rotarla.

Para una arquitectura productiva dentro de OCI, evaluar **Instance Principals + Dynamic Groups + IAM Policies** para evitar distribuir API signing keys en las VMs.

### 4.8 Checklist de preparacion de VM

Antes de clonar el repositorio:

```text
VM OCI operativa                    [ ]
Python 3.12                         [ ]
Git                                 [ ]
VS Code                             [ ]
Postman                             [ ]
OCI CLI                             [ ]
~/.oci/config o equivalente         [ ]
oci iam region list funciona        [ ]
Acceso HTTPS a GitHub/PyPI/CIMA     [ ]
```

---

## 5. Descarga del repositorio desde GitHub

El instructor publicara los proyectos en GitHub. El participante debe clonar el repositorio dentro de la VM:

```powershell
cd C:\workshops
git clone <URL_DEL_REPOSITORIO> oci-genai-two-projects
cd C:\workshops\oci-genai-two-projects
```

La estructura esperada es:

```text
oci-genai-two-projects/
├── oci-genai-oci-only/
└── oci-genai-litellm/
```

> Importante para publicar en GitHub: no subir `.env`, `.venv`, `__pycache__`, archivos de logs ni configuraciones con secretos. Subir `.env.example`, no `.env`.

---

## 6. Variables de entorno comunes

Cada proyecto debe tener su propio archivo `.env`.

Si existe `.env.example`, copiarlo:

```powershell
cp .env.example .env
```

Si no existe, crear `.env` con esta plantilla:

```dotenv
OCI_GENAI_API_KEY=<api-key>
OCI_GENAI_PROJECT_ID=<project-ocid>
OCI_GENAI_REGION=us-chicago-1
OCI_GENAI_VECTOR_STORE_ID=<vector-store-id>

OCI_GENAI_DEFAULT_MODEL=gemini
OCI_GENAI_MODELS_JSON={"gemini":"google.gemini-2.5-flash","grok":"xai.grok-4.3"}

CIMA_BASE_URL=https://cima.aemps.es/cima/rest
CIMA_MAX_RESULTS=2
CIMA_MAX_TO_EVALUATE=4
```

Para el Proyecto 2 agregar tambien:

```dotenv
LITELLM_PROXY_URL=http://localhost:4000
LITELLM_PROXY_PORT=4000
LITELLM_PROXY_API_KEY=anything
LITELLM_DEFAULT_MODEL=gemini
```

### 5.1 Por que usar alias de modelo

En vez de poner modelos reales en el codigo, se usa:

```dotenv
OCI_GENAI_MODELS_JSON={"gemini":"google.gemini-2.5-flash","grok":"xai.grok-4.3"}
```

Asi los scripts reciben alias logicos:

```powershell
python .\src\02_model_switching\02_hello_response.py grok
```

y la configuracion decide que modelo OCI real se usa.

---

# PARTE A - Proyecto 1: OCI GenAI directo

Ruta:

```powershell
cd C:\workshops\oci-genai-two-projects\oci-genai-oci-only
```

## 7. Crear entorno Python

```
  deactivate
  python3.12 -m venv .venv
  source .venv/bin/activate 
  python -m pip install -r requirements.txt
```

## 8. Validar configuracion

```powershell
python -c "from src.config import API_KEY, PROJECT_ID, REGION, VECTOR_STORE_ID; print('API_KEY:', bool(API_KEY)); print('PROJECT_ID:', bool(PROJECT_ID)); print('REGION:', REGION); print('VECTOR_STORE_ID:', bool(VECTOR_STORE_ID))"
```

Esperado:

```text
API_KEY: True
PROJECT_ID: True
REGION: us-chicago-1
VECTOR_STORE_ID: True
```

Si aparece error de URL sin `http://` o `https://`, revisar `OCI_GENAI_BASE_URL` si el proyecto lo usa. La URL completa debe ser:

```text
https://inference.generativeai.<REGION>.oci.oraclecloud.com/openai/v1
```

## 9. Stage 01 - Basic Responses API

Archivo:

```text
src/01_basic/01_hello_response.py
```

Ejecutar:

```powershell
python .\src\01_basic\01_hello_response.py
```

Objetivo: comprobar que la VM puede llamar OCI Generative AI usando el endpoint compatible con OpenAI.

## 10. Stage 02 - Model switching

Archivo:

```text
src/02_model_switching/02_hello_response.py
```

Ejecutar modelo por defecto:

```powershell
python .\src\02_model_switching\02_hello_response.py
```

Ejecutar Grok:

```powershell
python .\src\02_model_switching\02_hello_response.py grok
```

Objetivo: demostrar que el modelo se selecciona con alias logico y no modificando codigo.

## 11. Stage 03 - Vision multimodal

Archivo:

```text
src/03_multimodal/03_vision_recipe.py
```

Ejecutar:

```powershell
python .\src\03_multimodal\03_vision_recipe.py recipe_01.png
```

Objetivo: enviar una imagen de receta al modelo y recibir una descripcion libre. Este paso no produce una decision de negocio; solo demuestra entrada multimodal.

## 12. Stage 04 - Structured Output

Archivos principales:

```text
src/04_structured_output/05a_structured_recipe_validated.py
src/recipe_schema.py
```

Ejecutar:

```powershell
python .\src\04_structured_output\05a_structured_recipe_validated.py recipe_04.png
```

Ejecutar con Grok:

```powershell
python .\src\04_structured_output\05a_structured_recipe_validated.py recipe_04.png grok
```

Salida esperada:

```text
data/recipes/extracted/recipe_04_extracted.json
```

Objetivo: pasar de texto libre a JSON estructurado con campos como medicamento, concentracion, forma farmaceutica y cantidad.

## 13. Stage 05 - Validacion externa con CIMA

Archivo:

```text
src/05_external_validation/05b_validate_recipe_external.py
```

Ejecutar:

```powershell
python .\src\05_external_validation\05b_validate_recipe_external.py recipe_04.png
```

Salida esperada:

```text
data/recipes/extracted/recipe_04_external_validation.json
```

Objetivo: complementar la extraccion con una fuente externa. CIMA no reemplaza lo extraido; solo corrobora o deja evidencia de no confirmacion.

## 14. Stage 06 - Knowledge Base y RAG

Archivos:

```text
src/06_rag/06_upload_knowledge.py
src/06_rag/07_rag_policy.py
src/06_rag/08_recipe_with_rag.py
```

Politicas:

```text
data/knowledge/politica_datos_receta.md
data/knowledge/politica_procesamiento_recetas.md
data/knowledge/politica_revision_humana.md
```

### 13.1 Cargar o sincronizar la Knowledge Base

```powershell
python .\src\06_rag\06_upload_knowledge.py
```

Esperado:

```text
Uploaded and attached: politica_datos_receta.md
Uploaded and attached: politica_procesamiento_recetas.md
Uploaded and attached: politica_revision_humana.md
Knowledge base synchronization completed.
```

### 13.2 Probar RAG de forma aislada

```powershell
python .\src\06_rag\07_rag_policy.py
```

Debe responder la regla central:

```text
NOT_CONFIRMED no bloquea automaticamente una orden de Farmacia.
```

### 13.3 Ejecutar decision de Farmacia

```powershell
python .\src\06_rag\08_recipe_with_rag.py recipe_04.png
```

Resultado esperado para `recipe_04.png`:

```json
{
  "status": "READY_FOR_PHARMACY"
}
```

Interpretacion: aunque CIMA no confirme todos los atributos, la receta contiene medicamento, concentracion, presentacion y cantidad suficientes para construir la orden.

---

# PARTE B - Proyecto 2: OCI GenAI + LiteLLM

Ruta:

```powershell
cd C:\workshops\oci-genai-two-projects\oci-genai-litellm
```

## 15. Crear entorno Python

```deactivate
  python3.12 -m venv .venv
  source .venv/bin/activate 
  python -m pip install -r requirements.txt
```

Validar:

```
  which python
  which litellm
```

Ambos deben apuntar a `oci-genai-litellm\.venv`.

## 16. Dependencias criticas de LiteLLM Proxy

El `requirements.txt` del Proyecto 2 debe incluir:

```text
litellm[proxy]==1.97.0
fastapi>=0.136.3,<0.140
uvicorn>=0.33.0,<1.0
python-multipart>=0.0.27,<1.0
```

Validar:

```powershell
python -c "from importlib.metadata import version; print('LiteLLM:', version('litellm')); print('FastAPI:', version('fastapi')); print('WebSockets:', version('websockets'))"
```

## 17. Generar configuracion de LiteLLM

Archivo generador:

```text
src/00_generate_litellm_config.py
```

Ejecutar:

```powershell
python .\src\00_generate_litellm_config.py
```

Salida esperada:

```text
Generated: ...\src\litellm_config.yaml
  - gemini
  - grok
```

Validar que el YAML no contiene secretos:

```powershell
cat .\src\litellm_config.yaml
```

Debe verse asi:

```yaml
api_key: os.environ/OCI_GENAI_API_KEY
extra_headers:
  OpenAI-Project: os.environ/OCI_GENAI_PROJECT_ID
```

No debe mostrar la API key ni el OCID real.

## 18. Levantar LiteLLM Proxy

Terminal 1:

```powershell
litellm --config litellm_config.yaml --port 4000
```

Esperado:

```text
LiteLLM: Proxy initialized with Config
Set models:
    gemini
    grok
```

## 19. Probar modelos via Proxy

Terminal 2:

```powershell
cd ~/workshop/ai-workshop-genai/oci-genai-litellm
source .venv/bin/activate
```

Gemini:

```powershell
python -c "from openai import OpenAI; c=OpenAI(base_url='http://localhost:4000/v1', api_key='anything'); r=c.responses.create(model='gemini', input='Responde unicamente: LiteLLM con Gemini funciona.'); print(r.output_text)"
```

Grok:

```powershell
python -c "from openai import OpenAI; c=OpenAI(base_url='http://localhost:4000/v1', api_key='anything'); r=c.responses.create(model='grok', input='Responde unicamente: LiteLLM con Grok funciona.'); print(r.output_text)"
```

## 20. Ejecutar pipeline por etapas en Proyecto 2

### 19.1 Extraccion con LiteLLM

Archivo:

```text
src/stages/01_extract_recipe.py
```

Ejecutar:

```powershell
python .\src\stages\01_extract_recipe.py recipe_04.png gemini
python .\src\stages\01_extract_recipe.py recipe_04.png grok
```

Objetivo: demostrar que la imagen se procesa a traves del Proxy, no llamando OCI directamente desde el stage.

### 19.2 Validacion CIMA

Archivo:

```text
src/stages/02_validate_cima.py
```

Ejecutar:

```powershell
python .\src\stages\02_validate_cima.py recipe_04.png
```

No recibe modelo porque no usa LLM.

### 19.3 Decision de Farmacia con RAG y LiteLLM

Archivo:

```text
src/stages/03_pharmacy_decision.py
```

Ejecutar:

```powershell
python .\src\stages\03_pharmacy_decision.py recipe_04.png gemini
python .\src\stages\03_pharmacy_decision.py recipe_04.png grok
```

La salida debe contener:

```json
{
  "status": "READY_FOR_PHARMACY" | "PHARMACY_REVIEW" | "INSUFFICIENT_INFORMATION",
  "sources": ["EXTRACCION DE LA RECETA", "CIMA", "..."]
}
```

## 21. Levantar Recipe API para Postman

Archivo:

```text
src/recipe_api.py
```

Terminal 3:

```powershell
cd C:\workshops\oci-genai-two-projects\oci-genai-litellm
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python .\src\recipe_api.py
```

Esperado:

```text
Uvicorn running on http://127.0.0.1:8000
```

Validar health:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
```

## 22. Postman - Ejecutar pipeline completo

Request:

```text
POST http://127.0.0.1:8000/process-recipe
```

Body -> `form-data`:

| Key | Type | Value |
|---|---|---|
| `recipe` | File | `recipe_04.png` o `recipe_05.png` |
| `model` | Text | `gemini` o `grok` |

El endpoint ejecuta:

```text
01_extract_recipe -> 02_validate_cima -> 03_pharmacy_decision
```

Respuesta esperada:

```json
{
  "recipe": "recipe_04.png",
  "model": "gemini",
  "execution": "full_pipeline",
  "pipeline": {
    "extraction": {},
    "external_validation": {},
    "pharmacy_decision": {
      "status": "READY_FOR_PHARMACY"
    }
  }
}
```

## 23. Postman - Comparar modelos sin repetir Vision ni CIMA

Request:

```text
POST http://127.0.0.1:8000/evaluate-recipe
```

Body -> `form-data`:

| Key | Type | Value |
|---|---|---|
| `recipe` | Text | `recipe_05.png` |
| `model` | Text | `grok` |

Este endpoint reutiliza:

```text
recipe_05_extracted.json
recipe_05_external_validation.json
```

y solo reejecuta:

```text
03_pharmacy_decision.py
```

Esto permite comparar Gemini vs Grok sobre el mismo input sin repetir costos de Vision y CIMA.

---

## 24. Casos esperados de validacion

| Receta | Caracteristica | Resultado esperado |
|---|---|---|
| `recipe_04.png` | Contiene medicamento, concentracion, presentacion y cantidad | Normalmente `READY_FOR_PHARMACY`, aunque CIMA no confirme todo |
| `recipe_05.png` | Incluye campos ambiguos o incompletos como `Joringa.` sin concentracion/presentacion | Normalmente `PHARMACY_REVIEW` o `INSUFFICIENT_INFORMATION`, segun interpretacion del modelo y politicas |

Nota: la variacion entre modelos es esperada. El objetivo del Proyecto 2 no es hacer que todos los modelos respondan identicamente, sino demostrar como LiteLLM permite enrutar modelos y como la observabilidad posterior puede comparar calidad, trazabilidad y consistencia.

---

## 25. Checklist antes de pasar a LangSmith

| Validacion | Debe estar OK |
|---|---|
| Proyecto 1 ejecuta Stage 01 a Stage 06 | Si |
| Knowledge Base sincronizada con `06_upload_knowledge.py` | Si |
| `07_rag_policy.py` recupera politicas | Si |
| `recipe_04.png` llega a decision de Farmacia | Si |
| Proyecto 2 genera `litellm_config.yaml` sin secretos | Si |
| LiteLLM Proxy responde con `gemini` y `grok` | Si |
| `01_extract_recipe.py` usa LiteLLM | Si |
| `03_pharmacy_decision.py` usa LiteLLM + File Search | Si |
| `recipe_api.py` responde `/health` | Si |
| Postman ejecuta `/process-recipe` | Si |
| Postman ejecuta `/evaluate-recipe` | Si |

---

## 26. Troubleshooting frecuente

### PowerShell no permite activar el virtual environment

Error:

```text
running scripts is disabled on this system
```

Solucion:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### `ModuleNotFoundError: No module named openai`

Causa: terminal sin `.venv` activo.

Validar:

```powershell
python -c "import sys; print(sys.executable)"
```

### LiteLLM usa el `.venv` de otro proyecto

Validar:

```powershell
Get-Command litellm | Select-Object Source
```

Debe apuntar a:

```text
...\oci-genai-litellm\.venv\Scripts\litellm.exe
```

### Falta `websockets`

Causa: se instalo `litellm` base y no `litellm[proxy]`.

Solucion:

```powershell
python -m pip install "litellm[proxy]==1.97.0"
```

### Error de FastAPI con LiteLLM Proxy

Usar:

```text
fastapi>=0.136.3,<0.140
```

### Puerto 8000 ocupado

Validar:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object LocalAddress, LocalPort, OwningProcess
```

Detener proceso:

```powershell
Stop-Process -Id <PID>
```

### No aparece `READY_FOR_PHARMACY`

Revisar:

1. JSON de extraccion.
2. JSON de CIMA.
3. Politicas cargadas en Vector Store.
4. Si `sources` incluye politicas.
5. Si el modelo cambio entre extraccion y decision.

---

## 27. Guia de publicacion en GitHub

Antes de publicar:

```powershell
Get-ChildItem -Recurse -Force -Directory -Filter .venv
Get-ChildItem -Recurse -Force -Directory -Filter __pycache__
Get-ChildItem -Recurse -Force -File -Filter .env
```

No publicar:

```text
.env
.venv/
__pycache__/
litellm_config.yaml si contiene valores generados especificos de un entorno
*.log
```

Publicar:

```text
.env.example
README.md
requirements.txt
src/
data/knowledge/
data/recipes/imagenes_sanitizadas
```

Ejemplo de `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
*.pyc
*.log
.DS_Store
src/litellm_config.yaml
```

Mensaje para los participantes: cada uno debe crear su propio `.env` dentro de la VM con sus credenciales y OCIDs.

---
