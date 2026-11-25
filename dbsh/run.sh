#!/usr/bin/env bash
set -euo pipefail

# ─── dbsh — Docker-compose Database CLI wrapper ───
# Opens a DB shell (or runs a query) in the running DB container of a compose project.
# Credentials are read from the container's environment, so compose has already
# resolved ${VAR}, .env and env_file for us.
#
# Usage:
#   grab exec dbsh                     # interactive shell
#   grab exec dbsh "SELECT 1;"         # run a query
#   grab exec dbsh -f dump.sql         # execute a SQL file (or pipe it on stdin)
#   grab exec dbsh --service mydb      # target a specific compose service
#   grab exec dbsh --compose dev       # use docker-compose.dev.yml (or an exact path)
#   grab exec dbsh --info              # show detected connection info

BOLD='\033[1m'
DIM='\033[2m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

die() { echo -e "${RED}error:${NC} $*" >&2; exit 1; }
info() { echo -e "${CYAN}dbsh:${NC} $*" >&2; }

# ─── Resolve --compose: exact path, or a suffix like "dev" ───
find_compose_file() {
    local custom="$1"
    [[ -f "$custom" ]] && { echo "$custom"; return; }
    for pattern in \
        "docker-compose.${custom}.yml" "docker-compose.${custom}.yaml" \
        "docker-compose-${custom}.yml" "docker-compose-${custom}.yaml" \
        "compose.${custom}.yml"        "compose.${custom}.yaml" \
        "compose-${custom}.yml"        "compose-${custom}.yaml"; do
        [[ -f "$pattern" ]] && { echo "$pattern"; return; }
    done
    die "No compose file found for '${custom}'. Tried exact path and suffixes (docker-compose.${custom}.yml, compose-${custom}.yaml, ...)"
}

detect_db_type() {
    case "$1" in
        *postgres*|*postgis*|*pgvector*|*timescale*) echo "postgres" ;;
        *mariadb*)   echo "mariadb" ;;
        *mysql*)     echo "mysql" ;;
        *mongo*)     echo "mongo" ;;
        *)           echo "unknown" ;;
    esac
}

# Value of VAR in the container env (loaded in CONTAINER_ENV), empty if unset.
env_get() { awk -F= -v k="$1" '$1 == k { sub(/^[^=]*=/, ""); print; exit }' <<< "$CONTAINER_ENV"; }

extract_connection() {
    case "$1" in
        postgres)
            DB_USER=$(env_get POSTGRES_USER)
            DB_PASS=$(env_get POSTGRES_PASSWORD)
            DB_NAME=$(env_get POSTGRES_DB)
            DB_USER="${DB_USER:-postgres}"
            DB_NAME="${DB_NAME:-$DB_USER}"
            ;;
        mysql|mariadb)
            # MARIADB_* first, MYSQL_* is the compat name both images accept
            DB_USER=$(env_get MARIADB_USER); DB_USER="${DB_USER:-$(env_get MYSQL_USER)}"
            DB_PASS=$(env_get MARIADB_PASSWORD); DB_PASS="${DB_PASS:-$(env_get MYSQL_PASSWORD)}"
            DB_NAME=$(env_get MARIADB_DATABASE); DB_NAME="${DB_NAME:-$(env_get MYSQL_DATABASE)}"
            if [[ -z "$DB_USER" ]]; then
                DB_USER="root"
                DB_PASS=$(env_get MARIADB_ROOT_PASSWORD); DB_PASS="${DB_PASS:-$(env_get MYSQL_ROOT_PASSWORD)}"
            fi
            ;;
        mongo)
            DB_USER=$(env_get MONGO_INITDB_ROOT_USERNAME)
            DB_PASS=$(env_get MONGO_INITDB_ROOT_PASSWORD)
            DB_NAME=$(env_get MONGO_INITDB_DATABASE)
            DB_NAME="${DB_NAME:-admin}"
            ;;
    esac
}

main() {
    local compose_file="" service="" query="" sql_file="" show_info=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --compose|-c)  compose_file="$2"; shift 2 ;;
            --service|-s)  service="$2"; shift 2 ;;
            -f|--file)     sql_file="$2"; shift 2 ;;
            --info)        show_info=1; shift ;;
            --help|-h)     usage; exit 0 ;;
            -*)            die "Unknown option: $1" ;;
            *)             query="${query:+$query }$1"; shift ;;
        esac
    done

    [[ -n "$sql_file" && ! -f "$sql_file" ]] && die "SQL file not found: $sql_file"

    # Without --compose, docker compose finds the file itself (compose.yaml, override, COMPOSE_FILE...)
    local dc=(docker compose)
    if [[ -n "$compose_file" ]]; then
        compose_file=$(find_compose_file "$compose_file")
        dc+=(-f "$compose_file")
        info "Using ${DIM}${compose_file}${NC}"
    fi

    # Running services only: we need a container to exec into anyway.
    local running
    running=$("${dc[@]}" ps --format '{{.Service}} {{.Image}}') || die "docker compose ps failed (no compose file here?)"
    [[ -z "$running" ]] && die "No running service. Start the DB with: docker compose up -d"

    local svc image
    if [[ -z "$service" ]]; then
        while read -r svc image; do
            [[ $(detect_db_type "$image") != unknown ]] && { service="$svc"; break; }
        done <<< "$running"
        [[ -z "$service" ]] && die "No running database service (postgres, mysql, mariadb, mongo). Running: $(cut -d' ' -f1 <<< "$running" | paste -sd' ')"
    fi

    image=$(awk -v s="$service" '$1 == s { print $2; exit }' <<< "$running")
    [[ -z "$image" ]] && die "Service '$service' is not running. Start it with: ${dc[*]} up -d $service"

    local db_type container
    db_type=$(detect_db_type "$image")
    [[ "$db_type" == "unknown" ]] && die "Unsupported database image: $image"
    container=$("${dc[@]}" ps -q "$service" | head -n1)

    info "Service ${BOLD}${service}${NC} ${DIM}(${db_type})${NC}"

    CONTAINER_ENV=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$container")
    DB_USER="" DB_PASS="" DB_NAME=""
    extract_connection "$db_type"

    if [[ $show_info -eq 1 ]]; then
        echo -e "${BOLD}Connection info:${NC}"
        echo -e "  compose:   ${compose_file:-<default>}"
        echo -e "  service:   ${service}"
        echo -e "  container: ${container:0:12}"
        echo -e "  type:      ${db_type}"
        echo -e "  image:     ${image}"
        echo -e "  user:      ${DB_USER:-<not set>}"
        echo -e "  password:  ${DB_PASS:+****}"
        echo -e "  database:  ${DB_NAME:-<not set>}"
        exit 0
    fi

    # Password goes through the env, not argv: no "insecure password" warning, not in `ps` inside the container.
    local exec_opts=(-i) cmd=()
    case "$db_type" in
        postgres)
            exec_opts+=(-e "PGPASSWORD=$DB_PASS")
            cmd=(psql -U "$DB_USER" -d "$DB_NAME")
            [[ -n "$query" ]] && cmd+=(-c "$query")
            ;;
        mysql|mariadb)
            exec_opts+=(-e "MYSQL_PWD=$DB_PASS")
            # mariadb >= 11 images no longer ship the `mysql` binary
            [[ "$db_type" == mariadb ]] && cmd=(mariadb) || cmd=(mysql)
            cmd+=(-u "$DB_USER")
            [[ -n "$DB_NAME" ]] && cmd+=("$DB_NAME")
            [[ -n "$query" ]] && cmd+=(-e "$query")
            ;;
        mongo)
            cmd=(mongosh)
            [[ -n "$DB_USER" && -n "$DB_PASS" ]] && cmd+=(-u "$DB_USER" -p "$DB_PASS" --authenticationDatabase admin)
            cmd+=("$DB_NAME")
            [[ -n "$query" ]] && cmd+=(--eval "$query")
            ;;
    esac

    if [[ -n "$sql_file" ]]; then
        exec docker exec "${exec_opts[@]}" "$container" "${cmd[@]}" < "$sql_file"
    fi
    # TTY only for a real interactive shell, so `cat dump.sql | dbsh` works too
    if [[ -z "$query" && -t 0 && -t 1 ]]; then
        info "Opening interactive ${db_type} shell..."
        exec_opts+=(-t)
    fi
    exec docker exec "${exec_opts[@]}" "$container" "${cmd[@]}"
}

usage() {
    echo -e "${BOLD}dbsh${NC} — Docker-compose Database CLI wrapper"
    echo ""
    echo -e "${BOLD}USAGE${NC}"
    echo "  grab exec dbsh [options] [query]"
    echo ""
    echo -e "${BOLD}OPTIONS${NC}"
    echo "  -s, --service <name>    Target a specific compose service"
    echo "  -c, --compose <file>    Compose file: exact path or suffix (dev → docker-compose.dev.yml)"
    echo "  -f, --file <path>       Execute a SQL file (stdin works too)"
    echo "      --info              Show detected connection info and exit"
    echo "  -h, --help              Show this help"
    echo ""
    echo -e "${BOLD}EXAMPLES${NC}"
    echo "  grab exec dbsh                          # interactive DB shell"
    echo "  grab exec dbsh \"SELECT * FROM users;\"   # run a query"
    echo "  grab exec dbsh -f migrations/init.sql   # run a SQL file"
    echo "  grab exec dbsh -s postgres_db           # target specific service"
    echo "  grab exec dbsh --info                   # show connection details"
    echo ""
    echo -e "${BOLD}SUPPORTED DATABASES${NC}"
    echo "  PostgreSQL, MySQL, MariaDB, MongoDB (the DB service must be running)"
}

main "$@"
