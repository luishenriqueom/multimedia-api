# Multimedia API

API para upload, gerenciamento e consulta de arquivos de mídia (imagens, vídeos e áudios) com autenticação de usuários.

## Principais Funcionalidades

- Autenticação de usuários (registro, login, alteração de perfil e senha)
- Upload de mídia: imagem, vídeo e áudio
- Extração de metadados de imagens (EXIF, resolução, profundidade de cor, DPI)
- Extração de metadados de vídeos (duração, codecs, resolução, frame rate, etc)
- Extração de metadados de áudio (duração, bitrate, sample rate, etc)
- Geração de thumbnails para imagens e vídeos
- Geração de diferentes resoluções para vídeos (renditions 480p, 720p, 1080p)
- Organização de mídias por tags e proprietário
- Listagem e busca das mídias do usuário
- Download seguro das mídias pelo S3 (pré-assinadas)
- API protegida por autenticação JWT

## Tecnologias Utilizadas

- [FastAPI](https://fastapi.tiangolo.com/): framework principal de backend
- PostgreSQL: banco de dados relacional principal
- SQLAlchemy: ORM para banco relacional
- Alembic: migração de banco de dados
- AWS S3 (ou compatível): armazenamento dos arquivos de mídia
- [ffmpeg-python](https://github.com/kkroening/ffmpeg-python): processamento de vídeos
- [Pillow](https://python-pillow.org/): processamento de imagens

## Estrutura dos Diretórios

- `app/`: código-fonte da API (rotas, modelos, schemas, crud, utilitários)
- `alembic/`: arquivos de migrações
- `requirements.txt`: dependências do projeto
- `Dockerfile` & `docker-compose.yml`: configuração de containers

## Como Executar Localmente

1. Clone o repositório
2. Renomeie `.env.example` para `.env` e configure as variáveis (AWS, banco etc)
3. Suba os containers com Docker Compose:
   ```bash
   docker-compose up --build
   ```
4. A API estará disponível em: [http://localhost:8000/docs](http://localhost:8000/docs)

## Principais Rotas

- `POST   /auth/register` – registrar novo usuário
- `POST   /auth/login` – login do usuário (JWT)
- `GET    /users/me` – informações do usuário logado
- `PUT    /users/me` – editar perfil
- `POST   /media/upload/image` – upload de imagem
- `POST   /media/upload/video` – upload de vídeo
- `POST   /media/upload/audio` – upload de áudio
- `GET    /media/` – lista suas mídias
- `DELETE /media/{media_id}` – deleta mídia

## Observações

- Recomenda-se usar o ambiente Docker, que já provisiona o banco PostgreSQL.
- Os uploads são armazenados diretamente no S3; é necessário configurar as chaves AWS corretamente.
- Todos os endpoints de mídia requerem autenticação.
- Documentação interativa: `/docs` (Swagger) e `/redoc` (Redoc).

---

Desenvolvido para gestão de acervos multimídia pessoais protegidos. Suporte pronto para imagens, vídeos e áudios. Qualquer dúvida, abra um issue.
