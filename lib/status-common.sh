#!/usr/bin/env bash

unit_icon() {
    local alias="$1"
    local unit="$2"
    local kind="${3:-service}"
    local active result icon started
    active=$(systemctl is-active "$unit" 2>/dev/null || true)
    result=$(systemctl show "$unit" -p Result --value 2>/dev/null || true)

    if [[ "$kind" == job ]]; then
        started=$(systemctl show "$unit" -p ExecMainStartTimestampMonotonic --value 2>/dev/null || true)
        case "$active" in
            active|activating) icon='⏳' ;;
            failed) icon='❌' ;;
            inactive)
                if [[ -z "$started" || "$started" == 0 ]]; then
                    printf '⚪ %s: нет сведений о запуске\n' "$alias"
                    return
                fi
                [[ "$result" == success ]] && icon='✅' || icon='❌'
                alias="$alias: последнее выполнение"
                ;;
            *) icon='❔' ;;
        esac
    elif [[ "$kind" == timer ]]; then
        case "$active" in
            active) icon='✅' ;;
            failed) icon='❌' ;;
            inactive) icon='⏸' ;;
            activating) icon='⏳' ;;
            *) icon='❔' ;;
        esac
    else
        case "$active" in
            active) icon='✅' ;;
            failed) icon='❌' ;;
            inactive) icon='⏹' ;;
            activating) icon='⏳' ;;
            *) icon='❔' ;;
        esac
    fi
    printf '%s %s\n' "$icon" "$alias"
}

timer_next() {
    local alias="$1"
    local unit="$2"
    local next formatted
    next=$(systemctl show "$unit" -p NextElapseUSecRealtime --value 2>/dev/null || true)
    formatted=$(date -d "$next" '+%d.%m %H:%M' 2>/dev/null || true)
    printf '🕒 %s: %s\n' "$alias" "${formatted:-не запланирован}"
}
