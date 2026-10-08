# System Metrics Agent

Agent Python qui collecte CPU, RAM et charge système (psutil + commande
`uptime`) et les envoie à une API FastAPI. Ce fork contient le travail du TP
DevOps INGC2 : conteneurisation, Docker Compose et pipeline CI/CD.

## Rapport TP DevOps (INGC2)

**Étudiant :** À COMPLÉTER · **Travail :** individuel

| Livrable | Lien |
|---|---|
| Fork | https://github.com/À_COMPLÉTER/system_metrics_agent |
| Image API | https://hub.docker.com/r/À_COMPLÉTER/system-metrics-api |
| Image agent | https://hub.docker.com/r/À_COMPLÉTER/system-metrics-agent |
| Pipeline vert | À COMPLÉTER (lien du run) |
| Pipeline rouge (Trivy) | À COMPLÉTER (lien du run) |

### Choix techniques

- **Image de base `python:3.12.15-slim-trixie`.** Version figée jusqu'au patch
  et à la distribution, pour que deux builds à une semaine d'écart donnent la
  même chose. J'ai écarté Alpine : psutil et uvloop n'y ont pas toujours de
  wheel, il faudrait alors compiler (gcc, headers), et musl se comporte
  différemment de glibc. Le gain de taille ne compense pas ce risque.
- **Multi-stage.** Le stage `builder` crée un virtualenv dans `/opt/venv` et
  installe les dépendances ; l'image finale ne récupère que ce dossier et le
  code. `requirements.txt` est copié avant le code, donc tant qu'il ne change
  pas, la couche pip reste en cache.
- **Dépendances séparées.** `requirements.txt` ne contient que le runtime ;
  pytest, black et flake8 sont dans `requirements-dev.txt` et n'arrivent pas en
  production (moins de taille, moins de surface pour Trivy). Les versions sont
  figées, Dependabot se charge de proposer les mises à jour.
- **Sécurité.** Utilisateur système non-root (UID 10001), aucun secret dans
  l'image, `.env` exclu par le `.dockerignore` (avec `.git`, `.venv`, `tests`,
  les caches).
- **Prod.** `uvicorn` sans `--reload`, sur `0.0.0.0:8000`, `EXPOSE 8000`. Le
  `HEALTHCHECK` passe par `urllib` de Python plutôt que par curl, absent de
  l'image slim : inutile d'ajouter un paquet juste pour ça.
- **`uptime` dans l'agent.** La commande n'existe pas dans l'image slim, le
  collecteur levait donc une erreur à chaque cycle. Elle est fournie par le
  paquet Debian `procps`, que j'installe avec `--no-install-recommends` dans
  l'image de l'agent uniquement (l'API n'en a pas besoin).
- **Config à l'exécution.** `METRICS_ENDPOINT`, `COLLECTION_INTERVAL` et
  `REQUEST_TIMEOUT` ne sont pas figés dans l'image, ils viennent du `.env` via
  Compose ou de `-e` avec `docker run`.

**Tailles obtenues (`docker images`) :** API : À COMPLÉTER Mo, agent :
À COMPLÉTER Mo (image de base seule : À COMPLÉTER Mo).

**Agent conteneurisé et vraies métriques.** Docker ne virtualise pas
`/proc/meminfo` ni `/proc/loadavg` : sur mon Ubuntu, la RAM totale remontée
par l'agent conteneurisé est la même que celle de `free -b` sur la machine.
L'agent ignore donc les limites cgroup de son conteneur, et il remonte l'ID
du conteneur comme hostname au lieu du nom de la machine (sous Docker Desktop
ce serait même la VM Linux et pas le PC). En vrai déploiement, il faut soit
installer l'agent directement sur la machine (service systemd), soit le
lancer avec `pid: host`, le `/proc` de l'hôte monté en lecture seule et le
vrai hostname, comme le fait node-exporter de Prometheus.

### Pipeline (`.github/workflows/ci-cd.yml`)

Job `test` : pytest avec couverture XML, puis analyse SonarQube (SonarCloud)
avec `sonar.qualitygate.wait=true`, ce qui fait échouer le job si la Quality
Gate n'est pas validée. Job `build-scan-push` (`needs: test`, matrice
api/agent) : build avec `load: true`, scan Trivy bloquant sur les
vulnérabilités HIGH/CRITICAL corrigeables, puis `docker push` des tags SHA et
`latest` uniquement sur un push vers `main`. Je pousse l'image qui vient
d'être scannée, pas un rebuild. L'action Trivy est épinglée sur un SHA de
commit, parce que ses tags ont été détournés lors de l'attaque de mars 2026.
Bonus : cache `type=gha`, rapport SARIF dans l'onglet Security, Dependabot.

Secrets GitHub : `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (access token, pas le
mot de passe), `SONAR_TOKEN`, `SONAR_HOST_URL`. Aucun secret dans le dépôt.

**Échec volontaire :** À COMPLÉTER.

### Difficultés rencontrées

- `pytest -q` ne passait pas : les tests étaient dans `app/tests/` alors que le
  README annonçait `tests/` et un `test_api.py` qui n'existait pas. Je les ai
  déplacés à la racine et j'ai écrit les tests de l'API, de la config et de
  l'agent (20 tests, 86 % de couverture).
- Deux tests du collecteur échouaient sous Windows : `get_load_average`
  renvoie `None` sans appeler `uptime` sur cet OS, donc le mock n'était
  jamais utilisé. La plateforme est maintenant simulée dans les tests.
- `requirements.txt` déclarait `httpx2`, qui n'est pas le paquet `httpx`
  qu'attend le `TestClient` de FastAPI : impossible de tester l'API sans le
  remplacer.
- L'ancien `pipeline.yaml` visait Python 3.14.6 et déployait par SSH vers un
  chemin Windows, je l'ai remplacé. `app/montFichier.py` (import inutilisé,
  code mort) a été supprimé.
- À COMPLÉTER si autre chose bloque (SonarCloud, Docker Hub...).

## Lancer le projet

### En local (Python 3.11+)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
uvicorn app.api:app --reload     # terminal 1
python -m app.agent              # terminal 2
pytest -q --cov=app
```

Sans `.env`, l'agent envoie par défaut vers `http://127.0.0.1:8000/metrics`.

### Avec Docker Compose

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost:8000/metrics/latest
```

## Endpoints

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/health` | état de l'API (`{"status": "ok"}`) |
| POST | `/metrics` | réception d'une métrique (201) |
| GET | `/metrics` | toutes les métriques reçues |
| GET | `/metrics/latest` | dernière métrique (404 si aucune) |

## Structure

```text
app/            agent.py, api.py, collector.py, config.py, formatter.py, sender.py
tests/          tests pytest de chaque module
Dockerfile.api  Dockerfile.agent  docker-compose.yml  .dockerignore
sonar-project.properties  .env.example  .github/workflows/ci-cd.yml
```
