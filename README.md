# Workshop: OCI Generative AI y procesamiento multimodal

Este workshop construye un flujo de procesamiento inteligente de imágenes, PDF y video con OCI Generative AI. Combina modelos multimodales, salida estructurada, validación externa y una base de conocimiento para producir conclusiones trazables.

## Objetivos de aprendizaje

Al finalizar, cada participante podrá:

- Consumir directamente Gemini o Grok mediante OCI Generative AI.
- Cambiar de modelo mediante configuración, sin modificar el código.
- Procesar y analizar contenido multimodal.
- Obtener respuestas JSON con un esquema validable.
- Contrastar la información con una fuente externa, como CIMA.
- Usar una base de conocimiento vectorizada local y RAG para fundamentar una conclusión con políticas del negocio.

![Arquitectura de OCI Generative AI](assets/oci-genai-architecture.png)

## Recorrido del workshop

| Etapa | Tema | Resultado |
|---|---|---|
| 1 | Consumo directo | Una llamada a Gemini o Grok a través de OCI Generative AI. |
| 2 | Cambio de modelo | Selección por alias lógico, sin editar código. |
| 3 | Multimodal | Procesamiento y análisis de imágenes, PDF o video según el modelo. |
| 4 | Salida estructurada | Respuesta JSON validable. |
| 5 | Validación externa | Evidencia complementaria desde CIMA. |
| 6 | Base vectorizada local y RAG | Conclusión basada en políticas institucionales recuperadas. |

```text
Contenido multimodal → OCI Generative AI → JSON estructurado
        → validación externa → ChromaDB / RAG → conclusión trazable
```

## Configuración de OCI Generative AI

Completa esta sección en la consola de OCI antes de ejecutar los laboratorios. Trabaja en una región compatible con los modelos del workshop —para esta guía, **US Midwest (Chicago)** (`us-chicago-1`)— y usa el compartment raíz de tu propio tenancy. Todos los nombres siguientes son valores de ejemplo que los participantes pueden reutilizar.

![Tenancy y región de OCI](assets/oci-console/01-tenant-region.jpg)

> **Autenticación:** este workshop usa IAM, no API keys de OCI Generative AI. Cloud Shell firma las solicitudes con la sesión del participante y la VM usa un instance principal. No guardes secretos de OCI en el repositorio ni en archivos `.env`.

### 1. Abrir OCI Generative AI y seleccionar el compartment

**Descripción:** En la consola, abre **Analytics & AI → Generative AI**. Confirma la región y usa el selector de compartment de cada página para trabajar en `<tu-tenancy> (root)`.

![Página inicial de OCI Generative AI](assets/oci-console/02-generative-ai-overview.jpg)

### 2. Crear el proyecto

**Descripción:** El proyecto organiza conversaciones, respuestas, archivos y sandboxes. Es requerido por las llamadas compatibles con la API de OpenAI que se usarán durante el workshop.

1. Abre **Projects** y selecciona **Create project**.
2. En el selector superior de **Compartment**, selecciona `<tu-tenancy> (root)`.
3. Completa el formulario:

| Campo | Valor |
|---|---|
| **Name** | `genai-workshop-project` |
| **Description** | `Proyecto para laboratorios de modelos multimodales y RAG` |
| **Response retention (hours)** | `720` |
| **Conversation retention (hours)** | `720` |
| **Memory / compaction** | Deshabilitado |

4. Selecciona **Create**. Cuando el proyecto esté activo, abre su detalle y copia el **Project OCID**.

![Formulario para crear un proyecto de Generative AI](assets/oci-console/12-project-form.jpg)

### 3. Validar modelos disponibles y preparar la configuración

**Descripción:** Abre **Playground → Chat**. En los selectores superiores usa el compartment `<tu-tenancy> (root)`, selecciona un modelo Gemini o Grok disponible y envía la prueba siguiente:

| Campo | Valor |
|---|---|
| **Compartment** | `<tu-tenancy> (root)` |
| **Model** | Un modelo Gemini o Grok disponible en `us-chicago-1` |
| **Type a message...** | `Resume en una oración qué es OCI Generative AI.` |

Durante el workshop se elegirá el modelo mediante configuración, no modificando el código.

![Playground Chat de OCI Generative AI](assets/oci-console/15-chat-playground.jpg)

Antes de continuar, crea `oci-genai-oci-only/.env` desde `.env.example` y registra los identificadores que utilizará la aplicación. Elige el modo de autenticación según dónde ejecutes los laboratorios:

```text
OCI_GENAI_REGION=us-chicago-1
OCI_GENAI_PROJECT_ID=<PROJECT_OCID>

# En OCI Cloud Shell
OCI_GENAI_AUTH_MODE=session
OCI_CONFIG_PROFILE=DEFAULT

# En la VM de OCI
OCI_GENAI_AUTH_MODE=instance_principal
```

## Preparación del entorno

Cada participante trabaja en su propio tenancy OCI y crea una VM Oracle Linux 9 con IP pública. La creación incluye una VCN, subnet pública, Internet Gateway, tabla de rutas y una security list que permite SSH por TCP/22 desde `0.0.0.0/0`.

![Arquitectura del entorno OCI del workshop](assets/oci-workshop-architecture.png)

> **Seguridad del workshop:** SSH abierto a Internet es solo para un laboratorio temporal. Destruye los recursos al terminar.

### 1. Abrir OCI Cloud Shell y crear la VM

**Descripción:** Cloud Shell ya incluye OCI CLI. El script genera una clave RSA compatible con FIPS, crea la red y despliega la VM.

```bash
git clone <URL_DEL_REPOSITORIO>
cd ai-workshop-genai/infrastructure
chmod +x create-vm.sh destroy-vm.sh
REGION=us-chicago-1 ./create-vm.sh
```

El script imprime la IP pública y el **Instance OCID**, y guarda los OCIDs de los recursos en `.create-vm-state.env` para facilitar la limpieza posterior. Conserva el Instance OCID para el siguiente paso.

### 2. Autorizar la VM con IAM

**Descripción:** La VM se autenticará mediante un *instance principal*. No requiere API key, archivo de clave privada ni secreto de OCI.

Primero crea el Dynamic Group. En tenancies con Identity Domains, la ruta es **Identity & Security → Domains → Default → Dynamic groups → Create dynamic group**. Completa:

| Campo | Valor |
|---|---|
| **Name** | `genai-workshop-vm` |
| **Description** | `VM del workshop autorizada para OCI Generative AI` |
| **Matching rules option** | `Match all rules defined below` |
| **Matching rules** | `ALL {instance.id = '<INSTANCE_OCID>'}` |

Reemplaza `<INSTANCE_OCID>` por el valor impreso por `create-vm.sh`; conserva las comillas simples de la regla. Luego selecciona **Create**.

![Formulario para crear un Dynamic Group](assets/oci-console/11-dynamic-group-form.jpg)

Después crea la política. **Ruta de consola:** **Identity & Security → Policies → Create Policy → Show manual editor**. Completa:

| Campo | Valor |
|---|---|
| **Name** | `genai-workshop-vm-policy` |
| **Description** | `Permite a la VM usar OCI Generative AI durante el workshop` |
| **Compartment** | `<tu-tenancy> (root)` |
| **Policy statements** | La sentencia mostrada debajo |

```text
allow dynamic-group genai-workshop-vm to manage generative-ai-family in tenancy
```

Selecciona **Create**. La política aplica al tenancy completo; úsala únicamente cuando cada participante trabaje en su propio tenancy. Si destruyes y recreas la VM, actualiza la regla del Dynamic Group con el nuevo OCID de la instancia.

![Editor manual para crear una política IAM](assets/oci-console/14-policy-manual-form.jpg)

> **Cloud Shell:** si el participante administra su propio tenancy, su sesión normalmente ya dispone de permisos para administrar recursos. Si usa un usuario sin privilegios, un administrador debe agregarlo a un grupo y crear una política equivalente para ese grupo en el tenancy.

### 3. Conectarse a la VM

**Descripción:** Oracle Linux utiliza el usuario `opc`.

```bash
ssh -o StrictHostKeyChecking=accept-new \
  -i ~/.ssh/workshop_oci \
  opc@<IP_PUBLICA_VM>
```

Valida la imagen y el nombre de la VM:

```bash
cat /etc/os-release
hostname
```

### 4. [Opcional] Destruir y recrear el entorno

**Descripción:** Ejecuta esta prueba antes del workshop para confirmar que no quedan recursos residuales entre participantes.

```bash
./destroy-vm.sh
```

Confirma escribiendo `DELETE`. El script termina la VM y elimina subnet, security list, tabla de rutas, Internet Gateway y VCN. Después puedes volver a crear el entorno:

```bash
REGION=us-chicago-1 ./create-vm.sh
```

Si la VM se creó con una versión anterior de `create-vm.sh` y no existe `.create-vm-state.env`, usa su OCID:

```bash
REGION=us-chicago-1 ./destroy-vm.sh --instance-id <OCID_DE_LA_VM>
```

## Instalación de software en la VM

Los laboratorios se ejecutan dentro de un entorno virtual de Python 3.12. Además de las dependencias de OCI Generative AI, se instala **ChromaDB** para la base vectorizada local y `sentence-transformers` para generar embeddings en la VM. No se crea ni se requiere un OCI Vector Store.

> **Tiempo estimado:** de 5 a 10 minutos. La primera ejecución de la etapa RAG descargará el modelo de embeddings seleccionado; requiere salida a Internet desde la VM.

### 1. Instalar paquetes base

**Descripción:** Conéctate como `opc` y ejecuta los siguientes comandos. Oracle Linux 9.8 admite el paquete `python3.12`; se invoca explícitamente porque `python3` continúa apuntando a Python 3.9.

```bash
sudo dnf install -y \
  git python3.12 python3.12-pip \
  curl wget unzip

python3.12 --version
git --version
```

### 2. Clonar el repositorio y crear el entorno virtual

**Descripción:** Sustituye `<URL_DEL_REPOSITORIO>` por la URL que recibió el participante. El entorno `.venv` aísla las bibliotecas del workshop del sistema operativo.

```bash
cd ~
git clone <URL_DEL_REPOSITORIO> ai-workshop-genai
cd ai-workshop-genai
git checkout upd-workshop

python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

Si el repositorio ya existe en la VM, entra en su directorio y ejecuta únicamente los últimos tres comandos.

### 3. Instalar las dependencias Python

**Descripción:** El archivo de requisitos contiene las librerías para OCI Generative AI, validación y RAG local. No uses `sudo pip`.

```bash
python -m pip install -r oci-genai-oci-only/requirements.txt
```

### 4. Validar ChromaDB y los embeddings locales

**Descripción:** Este comando crea la carpeta persistente `.chroma` en el repositorio y valida que ChromaDB puede abrir una colección. Los documentos y sus vectores permanecerán en el disco de cada VM.

```bash
python - <<'PY'
from pathlib import Path

import chromadb
import sentence_transformers

database_path = Path.cwd() / ".chroma"
client = chromadb.PersistentClient(path=str(database_path))
collection = client.get_or_create_collection("workshop_knowledge")

print(f"ChromaDB listo: {database_path}")
print(f"Colección: {collection.name}")
print(f"sentence-transformers: {sentence_transformers.__version__}")
PY
```

El resultado esperado incluye `ChromaDB listo`, el nombre de la colección `workshop_knowledge` y la versión de `sentence-transformers`.

### 5. Activar el entorno en cada conexión

**Descripción:** Cada nueva sesión SSH inicia sin el entorno virtual activo. Antes de ejecutar cualquier etapa del workshop, vuelve a activarlo:

```bash
cd ~/ai-workshop-genai
source .venv/bin/activate
```

Para salir del entorno virtual al terminar:

```bash
deactivate
```

> **Próxima etapa:** el código de `oci-genai-oci-only/src/06_rag/` se adaptará para cargar las políticas en esta colección local y recuperar el contexto antes de invocar el LLM.

## Estructura del repositorio

```text
ai-workshop-genai/
├── assets/                 # Diagrama de arquitectura
├── infrastructure/         # Scripts OCI CLI para crear y destruir el entorno
├── oci-genai-oci-only/     # Parte 1: OCI Generative AI directo y RAG local
├── oci-genai-litellm/      # Parte 2: LiteLLM y abstracción de modelos
└── README.md               # Guía única del workshop
```

## Parte 1: OCI Generative AI directo

La carpeta `oci-genai-oci-only/` contiene las seis etapas centrales: consumo directo, cambio de modelo, multimodalidad, salida estructurada, validación CIMA y RAG con ChromaDB local.

## Parte 2: LiteLLM

La carpeta `oci-genai-litellm/` incorpora LiteLLM como proxy local para enrutar y comparar modelos sin mezclar esta abstracción con la implementación directa de OCI Generative AI.
