#!/usr/bin/env bash
set -euo pipefail

# ─── dbc — Docker-compose Database CLI wrapper ───
# Auto-detects DB connection info from docker-compose and runs queries
# without needing to specify credentials manually.
#
# Usage:
#   grab exec dbc                     # interactive shell
#   grab exec dbc "SELECT 1;"         # run a query
#   grab exec dbc -f dump.sql         # execute a SQL file
#   grab exec dbc --service mydb      # target a specific compose service
#   grab exec dbc --compose path.yml  # use a specific compose file
#   grab exec dbc --info              # show detected connection info

BOLD='\033[1m'
DIM='\033[2m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

die() { echo -e "${RED}error:${NC} $*" >&2; exit 1; }
info() { echo -e "${CYAN}dbc:${NC} $*" >&2; }
warn() { echo -e "${YELLOW}warn:${NC} $*" >&2; }

# ─── Find docker-compose file ───
find_compose_file() {
    local custom="$1"
    if [[ -n "$custom" ]]; then
        # exact path — use as-is
        if [[ -f "$custom" ]]; then
            echo "$custom"
            return
        fi
        # treat as suffix: try common patterns like docker-compose.dev.yml, compose.local.yaml, etc.
        for pattern in \
            "docker-compose.${custom}.yml" "docker-compose.${custom}.yaml" \
            "docker-compose-${custom}.yml" "docker-compose-${custom}.yaml" \
            "compose.${custom}.yml"        "compose.${custom}.yaml" \
            "compose-${custom}.yml"        "compose-${custom}.yaml"; do
            if [[ -f "$pattern" ]]; then
                echo "$pattern"
                return
            fi
        done
        die "No compose file found for '${custom}'. Tried exact path and suffixes (docker-compose.${custom}.yml, compose-${custom}.yaml, ...)"
    fi
    for candidate in "docker-compose.yml" "docker-compose.yaml" "compose.yml" "compose.yaml"; do
        if [[ -f "$candidate" ]]; then
            echo "$candidate"
            return
        fi
    done
    die "No docker-compose file found in current directory"
}

# ─── Lightweight YAML value extractor ───
# Reads a value from a docker-compose file for a given service + key path.
# Handles both "KEY=value" entries in environment lists and "KEY: value" mappings.
yaml_get_env() {
    local file="$1" service="$2" var="$3"
    local in_service=0 in_env=0 indent=""

    while IFS= read -r line; do
        # detect service block (top-level under services:)
        if [[ "$line" =~ ^[[:space:]]{2,4}${service}: ]]; then
            in_service=1
            continue
        fi

        # if we're inside the target service
        if [[ $in_service -eq 1 ]]; then
            # detect leaving service block (another service at same indent)
            if [[ "$line" =~ ^[[:space:]]{2,4}[a-zA-Z_-]+: ]] && [[ ! "$line" =~ ^[[:space:]]{4,} ]]; then
                # same indent level as service name = new service
                if [[ "$line" =~ ^[[:space:]]{2}[a-zA-Z] ]] || [[ "$line" =~ ^[[:space:]]{4}[a-zA-Z] && ! "$line" =~ ^[[:space:]]{6} ]]; then
                    break
                fi
            fi

            # detect environment block
            if [[ "$line" =~ ^[[:space:]]+(environment): ]]; then
                in_env=1
                continue
            fi

            # detect other top-level keys within service (leaving environment)
            if [[ $in_env -eq 1 ]] && [[ "$line" =~ ^[[:space:]]{4,6}[a-zA-Z_-]+: ]] && [[ ! "$line" =~ ^[[:space:]]{6,}- ]]; then
                # check if it's a key at the same level as 'environment:' — means we left the env block
                local env_line_stripped="${line#"${line%%[![:space:]]*}"}"
                if [[ ! "$env_line_stripped" =~ ^- ]]; then
                    local leading="${line%%[![:space:]]*}"
                    if [[ ${#leading} -le 6 ]]; then
                        in_env=0
                    fi
                fi
            fi

            if [[ $in_env -eq 1 ]]; then
                # list style: - KEY=value
                if [[ "$line" =~ -[[:space:]]*${var}=(.*) ]]; then
                    local val="${BASH_REMATCH[1]}"
                    # strip surrounding quotes
                    val="${val%\"}" ; val="${val#\"}"
                    val="${val%\'}" ; val="${val#\'}"
                    echo "$val"
                    return
                fi
                # mapping style: KEY: value
                if [[ "$line" =~ ${var}:[[:space:]]+(.*) ]]; then
                    local val="${BASH_REMATCH[1]}"
                    val="${val%\"}" ; val="${val#\"}"
                    val="${val%\'}" ; val="${val#\'}"
                    echo "$val"
                    return
                fi
            fi
        fi
    done < "$file"
}

# ─── Get the image name for a service ───
yaml_get_image() {
    local file="$1" service="$2"
    local in_service=0

    while IFS= read -r line; do
        if [[ "$line" =~ ^[[:space:]]{2,4}${service}: ]]; then
            in_service=1
            continue
        fi
        if [[ $in_service -eq 1 ]]; then
            if [[ "$line" =~ ^[[:space:]]{2}[a-zA-Z] ]] && [[ ! "$line" =~ ^[[:space:]]{4,} ]]; then
                break
            fi
            if [[ "$line" =~ ^[[:space:]]+image:[[:space:]]+(.*) ]]; then
                local val="${BASH_REMATCH[1]}"
                val="${val%\"}" ; val="${val#\"}"
                val="${val%\'}" ; val="${val#\'}"
                echo "$val"
                return
            fi
        fi
    done < "$file"
}

# ─── Detect DB type from image name ───
detect_db_type() {
    local image="$1"
    case "$image" in
        *postgres*)  echo "postgres" ;;
        *mysql*)     echo "mysql" ;;
        *mariadb*)   echo "mariadb" ;;
        *mongo*)     echo "mongo" ;;
        *)           echo "unknown" ;;
    esac
}

# ─── Find the first DB service in compose file ───
find_db_service() {
    local file="$1"
    local services=()

    # extract service names
    local in_services=0
    while IFS= read -r line; do
        if [[ "$line" =~ ^services: ]]; then
            in_services=1
            continue
        fi
        if [[ $in_services -eq 1 ]]; then
            # top-level key outside services
            if [[ "$line" =~ ^[a-zA-Z] ]]; then
                break
            fi
            # service name (indented, ends with :)
            if [[ "$line" =~ ^[[:space:]]{2,4}([a-zA-Z_-]+): ]]; then
                services+=("${BASH_REMATCH[1]}")
            fi
        fi
    done < "$file"

    # find first service with a DB image
    for svc in "${services[@]}"; do
        local image
        image=$(yaml_get_image "$file" "$svc")
        local db_type
        db_type=$(detect_db_type "$image")
        if [[ "$db_type" != "unknown" ]]; then
            echo "$svc"
            return
        fi
    done
    die "No database service found in $file"
}

# ─── Extract connection info ───
extract_connection() {
    local file="$1" service="$2" db_type="$3"

    case "$db_type" in
        postgres)
            DB_USER=$(yaml_get_env "$file" "$service" "POSTGRES_USER")
            DB_PASS=$(yaml_get_env "$file" "$service" "POSTGRES_PASSWORD")
            DB_NAME=$(yaml_get_env "$file" "$service" "POSTGRES_DB")
            DB_USER="${DB_USER:-postgres}"
            DB_NAME="${DB_NAME:-$DB_USER}"
            ;;
        mysql)
            DB_USER=$(yaml_get_env "$file" "$service" "MYSQL_USER")
            DB_PASS=$(yaml_get_env "$file" "$service" "MYSQL_PASSWORD")
            DB_NAME=$(yaml_get_env "$file" "$service" "MYSQL_DATABASE")
            # fallback: root user with root password
            if [[ -z "$DB_USER" ]]; then
                DB_USER="root"
                DB_PASS=$(yaml_get_env "$file" "$service" "MYSQL_ROOT_PASSWORD")
            fi
            ;;
        mariadb)
            DB_USER=$(yaml_get_env "$file" "$service" "MARIADB_USER")
            DB_PASS=$(yaml_get_env "$file" "$service" "MARIADB_PASSWORD")
            DB_NAME=$(yaml_get_env "$file" "$service" "MARIADB_DATABASE")
            # fallback: MYSQL_* compat vars
            [[ -z "$DB_USER" ]] && DB_USER=$(yaml_get_env "$file" "$service" "MYSQL_USER")
            [[ -z "$DB_PASS" ]] && DB_PASS=$(yaml_get_env "$file" "$service" "MYSQL_PASSWORD")
            [[ -z "$DB_NAME" ]] && DB_NAME=$(yaml_get_env "$file" "$service" "MYSQL_DATABASE")
            if [[ -z "$DB_USER" ]]; then
                DB_USER="root"
                DB_PASS=$(yaml_get_env "$file" "$service" "MARIADB_ROOT_PASSWORD")
                [[ -z "$DB_PASS" ]] && DB_PASS=$(yaml_get_env "$file" "$service" "MYSQL_ROOT_PASSWORD")
            fi
            ;;
        mongo)
            DB_USER=$(yaml_get_env "$file" "$service" "MONGO_INITDB_ROOT_USERNAME")
            DB_PASS=$(yaml_get_env "$file" "$service" "MONGO_INITDB_ROOT_PASSWORD")
            DB_NAME=$(yaml_get_env "$file" "$service" "MONGO_INITDB_DATABASE")
            DB_USER="${DB_USER:-root}"
            DB_NAME="${DB_NAME:-admin}"
            ;;
    esac
}

# ─── Build and run the docker exec command ───
run_db_command() {
    local service="$1" db_type="$2" query="$3" sql_file="$4"

    # find the running container for this service
    local container
    container=$(docker compose ps -q "$service" 2>/dev/null) \
        || container=$(docker-compose ps -q "$service" 2>/dev/null) \
        || die "Cannot find running container for service '$service'. Is it running?"

    [[ -z "$container" ]] && die "Service '$service' is not running. Start it with: docker compose up -d $service"

    local cmd=()
    case "$db_type" in
        postgres)
            cmd=(psql -U "$DB_USER" -d "$DB_NAME")
            if [[ -n "$sql_file" ]]; then
                # pipe file through docker exec
                docker exec -i "$container" "${cmd[@]}" < "$sql_file"
                return
            elif [[ -n "$query" ]]; then
                cmd+=(-c "$query")
                docker exec -i "$container" "${cmd[@]}"
                return
            else
                # interactive
                docker exec -it "$container" "${cmd[@]}"
                return
            fi
            ;;
        mysql|mariadb)
            cmd=(mysql -u "$DB_USER")
            [[ -n "$DB_PASS" ]] && cmd+=(-p"$DB_PASS")
            [[ -n "$DB_NAME" ]] && cmd+=("$DB_NAME")
            if [[ -n "$sql_file" ]]; then
                docker exec -i "$container" "${cmd[@]}" < "$sql_file"
                return
            elif [[ -n "$query" ]]; then
                cmd+=(-e "$query")
                docker exec -i "$container" "${cmd[@]}"
                return
            else
                docker exec -it "$container" "${cmd[@]}"
                return
            fi
            ;;
        mongo)
            cmd=(mongosh)
            if [[ -n "$DB_USER" && -n "$DB_PASS" ]]; then
                cmd+=(-u "$DB_USER" -p "$DB_PASS" --authenticationDatabase admin)
            fi
            cmd+=("$DB_NAME")
            if [[ -n "$sql_file" ]]; then
                docker exec -i "$container" "${cmd[@]}" < "$sql_file"
                return
            elif [[ -n "$query" ]]; then
                cmd+=(--eval "$query")
                docker exec -i "$container" "${cmd[@]}"
                return
            else
                docker exec -it "$container" "${cmd[@]}"
                return
            fi
            ;;
    esac
}

# ─── Main ───
main() {
    local compose_file="" target_service="" query="" sql_file="" show_info=0

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --compose|-c)  compose_file="$2"; shift 2 ;;
            --service|-s)  target_service="$2"; shift 2 ;;
            -f|--file)     sql_file="$2"; shift 2 ;;
            --info)        show_info=1; shift ;;
            --help|-h)     usage; exit 0 ;;
            -*)            die "Unknown option: $1" ;;
            *)
                if [[ -z "$query" ]]; then
                    query="$1"
                else
                    query="$query $1"
                fi
                shift
                ;;
        esac
    done

    # resolve compose file
    compose_file=$(find_compose_file "$compose_file")
    info "Using ${DIM}${compose_file}${NC}"

    # resolve service
    if [[ -z "$target_service" ]]; then
        target_service=$(find_db_service "$compose_file")
    fi

    # detect DB type
    local image
    image=$(yaml_get_image "$compose_file" "$target_service")
    [[ -z "$image" ]] && die "Cannot read image for service '$target_service'"

    local db_type
    db_type=$(detect_db_type "$image")
    [[ "$db_type" == "unknown" ]] && die "Unsupported database image: $image"

    info "Service ${BOLD}${target_service}${NC} ${DIM}(${db_type})${NC}"

    # extract credentials
    DB_USER="" DB_PASS="" DB_NAME=""
    extract_connection "$compose_file" "$target_service" "$db_type"

    # validate file if provided
    if [[ -n "$sql_file" && ! -f "$sql_file" ]]; then
        die "SQL file not found: $sql_file"
    fi

    # --info: just print and exit
    if [[ $show_info -eq 1 ]]; then
        echo -e "${BOLD}Connection info:${NC}"
        echo -e "  compose:  ${compose_file}"
        echo -e "  service:  ${target_service}"
        echo -e "  type:     ${db_type}"
        echo -e "  image:    ${image}"
        echo -e "  user:     ${DB_USER:-<not set>}"
        echo -e "  password: ${DB_PASS:+****}"
        echo -e "  database: ${DB_NAME:-<not set>}"
        exit 0
    fi

    # run
    if [[ -z "$query" && -z "$sql_file" ]]; then
        info "Opening interactive ${db_type} shell..."
    fi

    run_db_command "$target_service" "$db_type" "$query" "$sql_file"
}

usage() {
    echo -e "${BOLD}dbc${NC} — Docker-compose Database CLI wrapper"
    echo ""
    echo -e "${BOLD}USAGE${NC}"
    echo "  grab exec dbc [options] [query]"
    echo ""
    echo -e "${BOLD}OPTIONS${NC}"
    echo "  -s, --service <name>    Target a specific compose service"
    echo "  -c, --compose <file>    Use a specific docker-compose file"
    echo "  -f, --file <path>       Execute a SQL file"
    echo "      --info              Show detected connection info and exit"
    echo "  -h, --help              Show this help"
    echo ""
    echo -e "${BOLD}EXAMPLES${NC}"
    echo "  grab exec dbc                          # interactive DB shell"
    echo "  grab exec dbc \"SELECT * FROM users;\"   # run a query"
    echo "  grab exec dbc -f migrations/init.sql   # run a SQL file"
    echo "  grab exec dbc -s postgres_db           # target specific service"
    echo "  grab exec dbc --info                   # show connection details"
    echo ""
    echo -e "${BOLD}SUPPORTED DATABASES${NC}"
    echo "  PostgreSQL, MySQL, MariaDB, MongoDB"
}

main "$@"
