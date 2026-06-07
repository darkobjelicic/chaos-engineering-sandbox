🇷🇸 Srpski | [🇬🇧 English](local-setup.en.md)

# Lokalni setup

## Sistemski zahtevi

| Resurs | Minimum |
|----------|---------|
| CPU | 4 jezgra |
| RAM | 8 GB (16 GB preporučeno za ceo stack) |
| Disk | 20 GB slobodnog prostora |
| OS | Linux / macOS |

---

## Potrebni alati

### Kontejneri i orkestracija

| Alat | Verzija | Instalacija |
|------|---------|---------|
| [Docker](https://docs.docker.com/engine/install/) | 24+ | `apt-get install docker-ce` |
| [Docker Compose](https://docs.docker.com/compose/install/) | v2.20+ | Uključen u Docker Desktop |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | v1.28+ | `apt-get install kubectl` |
| [kind](https://kind.sigs.k8s.io/docs/user/quick-start/) | v0.20+ | Binary sa GitHub releases |
| [Helm](https://helm.sh/docs/intro/install/) | v3.12+ | `apt-get install helm` |

### GitOps i secrets

| Alat | Verzija | Instalacija |
|------|---------|---------|
| [argocd CLI](https://argo-cd.readthedocs.io/en/stable/cli_installation/) | v2.10+ | Binary sa GitHub releases |
| [kubeseal](https://github.com/bitnami-labs/sealed-secrets#installation) | v0.26+ | Binary sa GitHub releases |

### Testiranje

| Alat | Verzija | Instalacija |
|------|---------|---------|
| [k6](https://k6.io/docs/get-started/installation/) | v0.50+ | Binary sa GitHub releases |

### Kvalitet koda

| Alat | Verzija | Instalacija |
|------|---------|---------|
| [pre-commit](https://pre-commit.com/#installation) | v3.0+ | `pipx install pre-commit` |

---

## Brza instalacija (Ubuntu 24.04)

### argocd CLI
```bash
curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
chmod +x argocd && sudo mv argocd /usr/local/bin/
```

### kubeseal
```bash
curl -sSL -o kubeseal.tar.gz "https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.36.6/kubeseal-0.36.6-linux-amd64.tar.gz"
tar -xzf kubeseal.tar.gz kubeseal
chmod +x kubeseal && sudo mv kubeseal /usr/local/bin/
rm kubeseal.tar.gz
```

### k6
```bash
curl -fsSL https://github.com/grafana/k6/releases/download/v0.57.0/k6-v0.57.0-linux-amd64.tar.gz -o k6.tar.gz
tar -xzf k6.tar.gz
sudo mv k6-v0.57.0-linux-amd64/k6 /usr/local/bin/
rm -rf k6.tar.gz k6-v0.57.0-linux-amd64
```

### pre-commit
```bash
sudo apt-get install -y pipx
pipx install pre-commit
pipx ensurepath
```

---

## Provera instalacije

```bash
docker --version
docker compose version
kubectl version --client
kind --version
helm version
argocd version --client
kubeseal --version
k6 version
pre-commit --version
```

---

## Lokalni razvoj (Docker Compose)

Pokretanje svih servisa lokalno bez Kubernetesa:

```bash
cp .env.example .env   # izmeniti vrednosti po potrebi
make dev-up
```

Servisi dostupni na:

| Servis | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Gateway | http://localhost:8000 |
| RabbitMQ UI | http://localhost:15672 (guest/guest) |
| Adminer (DB) | http://localhost:8081 |

Gašenje:
```bash
make dev-down
```

---

## Linux: inotify limiti (potrebno za Promtail)

Promtail prati log fajlove kontejnera putem inotify-ja. Podrazumevani Linux limiti su premali za kind klaster. Pokrenuti jednom pre `cluster-up.sh`:

```bash
sudo sysctl fs.inotify.max_user_instances=512
sudo sysctl fs.inotify.max_user_watches=524288
```

Za trajno čuvanje kroz reboot:
```bash
echo "fs.inotify.max_user_instances=512" | sudo tee -a /etc/sysctl.conf
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.conf
```

---

## Kompletan lokalni stack (Kubernetes + GitOps)

Pokretanje celog stack-a jednom komandom:

```bash
make cluster-up
```

Skripta će:
1. Kreirati kind klaster
2. Instalirati NGINX Ingress Controller
3. Instalirati cert-manager
4. Instalirati ArgoCD
5. ArgoCD automatski povlači sve ostalo iz ovog repo-a

Pristupne tačke nakon pokretanja:

```bash
make argocd-ui    # ArgoCD dashboard
make grafana-ui   # Grafana (metrike, logovi, tragovi)
```

Gašenje:
```bash
make cluster-down
```

---

## Pokretanje na sopstvenoj mašini (dva scenarija)

### Scenario A — Samo pokreni (clone i kreni)

Repo je potpuno autonoman i javno dostupan. Nije potrebna nikakva dodatna konfiguracija.

```bash
git clone https://github.com/darkobjelicic/chaos-engineering-sandbox.git
cd chaos-engineering-sandbox

# Samo Linux — potrebno za Promtail (videti inotify sekciju iznad)
sudo sysctl fs.inotify.max_user_instances=512
sudo sysctl fs.inotify.max_user_watches=524288

make cluster-up
```

Dodati u `/etc/hosts`:
```
127.0.0.1  bookstore.local api.bookstore.local grafana.monitoring.local
```

**Zašto ovo radi odmah:**
- Svi application secrets su plain literals u `kustomization.yaml` (dev kredencijali — bezbedno za lokalni sandbox)
- Sve Docker slike su javne na Docker Hub-u (`darko999/*`)
- ArgoCD se sinhronizuje iz javnog GitHub repo-a — autentifikacija nije potrebna
- Sve ostalo se povlači iz javnih Helm/kubectl registry-a tokom `cluster-up`

**Ograničenje:** Neće biti moguće push-ovati sopstvene izmene koda i imati CI/CD koji gradi nove slike — to zahteva Docker Hub kredencijale podešene u GitHub Actions.

---

### Scenario B — Fork i preuzmi ceo pipeline

Ako želiš sopstveni CI/CD pipeline koji gradi i deploy-uje tvoje izmene:

**1. Fork repo na GitHub-u**

**2. Ažurirati ArgoCD aplikaciju da pokazuje na tvoj fork:**
```yaml
# deploy/argocd/bookstore-app.yaml
spec:
  source:
    repoURL: https://github.com/TVOJE-IME/chaos-engineering-sandbox.git
```

**3. Ažurirati nazive slika u CD workflow-u:**
```yaml
# .github/workflows/cd.yml — zameniti sve pojave darko999 sa tvojim Docker Hub korisničkim imenom
image: TVOJE-DOCKERHUB-IME/api-gateway
# ... ponoviti za svaki servis
```

**4. Ažurirati nazive slika u kustomization overlay-u:**
```yaml
# deploy/overlays/kind/kustomization.yaml — zameniti darko999 sa tvojim Docker Hub korisničkim imenom
images:
- name: TVOJE-DOCKERHUB-IME/api-gateway
  newName: TVOJE-DOCKERHUB-IME/api-gateway
```

**5. Dodati GitHub Actions secrets** u Settings → Secrets → Actions svog forka:
```
DOCKER_USERNAME   tvoje Docker Hub korisničko ime
DOCKER_PASSWORD   tvoj Docker Hub access token
```

**6. Pokrenuti stack:**
```bash
make cluster-up
```

Od ovog trenutka, svaki push na `main` automatski gradi nove slike, ažurira tagove slika, a ArgoCD deploy-uje na lokalni klaster.
