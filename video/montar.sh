#!/usr/bin/env bash
# Monta o vídeo final da entrega (video/smartpark-final.mp4).
#
# Entradas:
#   video/gravacoes/cenaNN.mov   gravação da tela de cada cena do video/roteiro.md (.mov, .mp4 ou .m4v)
#   video/gravacoes/falaNN.m4a   narração de cada cena (.m4a, .wav, .mp3 ou .aac)
#   video/gravacoes/fala00.m4a   narração da abertura (opcional)
#   docs/apresentacao/abertura.mp4 ou motion.mp4 (gerados por docs/apresentacao/render.mjs)
#
# Cada cena vira 1920x1080, 30 fps; a narração substitui o áudio da gravação; se a fala for mais
# longa que o vídeo, o último quadro fica congelado até a fala acabar. Uma legenda pequena com o
# título da cena (tirado das linhas "## Cena NN · Título" do roteiro) aparece nos primeiros segundos.
#
# Uso:
#   video/montar.sh                  abertura (48 s) + cenas
#   video/montar.sh --intro motion   apresentação animada inteira + cenas
#   video/montar.sh --intro nenhuma  só as cenas
#   video/montar.sh --parcial        pula cenas sem gravação e usa silêncio onde falta fala
#   video/montar.sh --acelerar       acelera (até 2x) a gravação que for mais longa que a fala
# Variáveis (para testar): GRAVACOES, ROTEIRO, SAIDA, APRESENTACAO
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="$(dirname "$AQUI")"
GRAVACOES="${GRAVACOES:-$AQUI/gravacoes}"
ROTEIRO="${ROTEIRO:-$AQUI/roteiro.md}"
SAIDA="${SAIDA:-$AQUI/smartpark-final.mp4}"
APRESENTACAO="${APRESENTACAO:-$RAIZ/docs/apresentacao}"
INTRO="abertura"
PARCIAL=0
ACELERAR=0
FUNDO="0x07090d"

erro() { printf 'ERRO: %s\n' "$*" >&2; exit 1; }
aviso() { printf 'aviso: %s\n' "$*" >&2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --intro) INTRO="${2:-}"; shift 2 ;;
    --parcial) PARCIAL=1; shift ;;
    --acelerar) ACELERAR=1; shift ;;
    --saida) SAIDA="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) erro "opção desconhecida: $1 (veja --help)" ;;
  esac
done
case "$INTRO" in abertura|motion|nenhuma) ;; *) erro "--intro deve ser abertura, motion ou nenhuma" ;; esac

command -v ffmpeg >/dev/null || erro "ffmpeg não encontrado (brew install ffmpeg)"
command -v ffprobe >/dev/null || erro "ffprobe não encontrado (vem com o ffmpeg)"
[ -f "$ROTEIRO" ] || erro "roteiro não encontrado: $ROTEIRO"
[ -d "$GRAVACOES" ] || erro "pasta de gravações não encontrada: $GRAVACOES (crie e salve cenaNN.mov e falaNN.m4a nela)"
TEM_RSVG=1
command -v rsvg-convert >/dev/null || { TEM_RSVG=0; aviso "rsvg-convert não encontrado (brew install librsvg): sem legenda com o título"; }

duracao() { ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$1" | head -n1; }
achar() {   # achar <base> <ext...>: imprime o primeiro arquivo que existe
  local base="$1"; shift
  for e in "$@"; do [ -f "$base.$e" ] && { printf '%s' "$base.$e"; return 0; }; done
  return 1
}

# ---------- cenas do roteiro ----------
NUMS=(); TITULOS=()
while IFS= read -r linha; do
  n="$(printf '%s' "$linha" | sed -E 's/^## Cena ([0-9]{2}).*/\1/')"
  t="$(printf '%s' "$linha" | sed -E 's/^## Cena [0-9]{2}[[:space:]]*[·:-]?[[:space:]]*//')"
  NUMS+=("$n"); TITULOS+=("$t")
done < <(grep -E '^## Cena [0-9]{2}' "$ROTEIRO")
[ ${#NUMS[@]} -gt 0 ] || erro "nenhuma linha '## Cena NN · Título' em $ROTEIRO"

# ---------- conferência dos arquivos ----------
faltando=()
for n in "${NUMS[@]}"; do
  achar "$GRAVACOES/cena$n" mov mp4 m4v >/dev/null || faltando+=("cena$n.mov")
  achar "$GRAVACOES/fala$n" m4a wav mp3 aac >/dev/null || faltando+=("fala$n.m4a")
done
INTRO_ARQ=""
if [ "$INTRO" != "nenhuma" ]; then
  INTRO_ARQ="$APRESENTACAO/$INTRO.mp4"
  [ -f "$INTRO_ARQ" ] || faltando+=("$INTRO_ARQ (rode: cd docs/apresentacao && node render.mjs ...)")
fi
if [ ${#faltando[@]} -gt 0 ]; then
  printf 'Arquivos faltando em %s:\n' "$GRAVACOES" >&2
  printf '  - %s\n' "${faltando[@]}" >&2
  [ "$PARCIAL" = 1 ] || erro "grave os arquivos acima ou use --parcial para montar só com o que existe"
  aviso "--parcial: cenas sem gravação ficam de fora; falas faltando viram silêncio"
fi

TMP="$(mktemp -d "${TMPDIR:-/tmp}/smartpark-montar.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

xml() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }
legenda() {   # legenda <titulo> <num> <png>
  local titulo num larg
  titulo="$(xml "$1")"; num="$2"
  larg=$(( ${#1} * 15 + 150 ))
  cat > "$TMP/leg.svg" <<SVG
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">
  <rect x="48" y="958" rx="14" width="$larg" height="72" fill="#07090d" fill-opacity="0.82" stroke="#8b7cff" stroke-opacity="0.6"/>
  <rect x="64" y="976" rx="8" width="58" height="36" fill="#8b7cff"/>
  <text x="93" y="1001" text-anchor="middle" font-family="Helvetica Neue, Helvetica, Arial, sans-serif" font-size="20" font-weight="700" fill="#ffffff">$num</text>
  <text x="138" y="1002" font-family="Helvetica Neue, Helvetica, Arial, sans-serif" font-size="26" font-weight="600" fill="#edf1f7">$titulo</text>
</svg>
SVG
  rsvg-convert "$TMP/leg.svg" -o "$3"
}

# segmento <video> <audio ou ""> <titulo ou ""> <num> <saida>
segmento() {
  local video="$1" audio="$2" titulo="$3" num="$4" out="$5"
  local vdur adur dur pad fo
  vdur="$(duracao "$video")"; [ -n "$vdur" ] || erro "não consegui ler a duração de $video"
  adur=0; [ -n "$audio" ] && adur="$(duracao "$audio")"
  # --acelerar: gravação mais longa que a fala é acelerada (até 2x) para acabar junto com a fala
  local vel=1
  if [ "$ACELERAR" = 1 ] && [ -n "$audio" ]; then
    vel="$(awk -v v="$vdur" -v a="$adur" 'BEGIN { f = v / (a + 0.6); if (f < 1) f = 1; if (f > 2) f = 2; printf "%.4f", f }')"
    vdur="$(awk -v v="$vdur" -v f="$vel" 'BEGIN { printf "%.3f", v / f }')"
  fi
  read -r dur pad fo < <(awk -v v="$vdur" -v a="$adur" 'BEGIN { d = v; if (a + 0.6 > d) d = a + 0.6; p = d - v; f = (d - 0.6 < 6) ? d - 0.6 : 6; if (f < 0.8) f = 0.8; printf "%.3f %.3f %.3f\n", d, p, f }')
  local args=(-y -v error -i "$video")
  if [ -n "$audio" ]; then args+=(-i "$audio"); else args+=(-f lavfi -t "$dur" -i "anullsrc=r=48000:cl=stereo"); fi
  local fv="[0:v]setpts=PTS/$vel,scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=$FUNDO,setsar=1,fps=30"
  awk -v p="$pad" 'BEGIN { exit !(p > 0.001) }' && fv="$fv,tpad=stop_mode=clone:stop_duration=$pad"
  fv="$fv,format=yuv420p"
  local filtro
  if [ -n "$titulo" ] && [ "$TEM_RSVG" = 1 ]; then
    legenda "$titulo" "$num" "$TMP/leg.png"
    args+=(-loop 1 -t "$dur" -i "$TMP/leg.png")
    filtro="$fv[v0];[2:v]format=rgba,fade=t=in:st=0.3:d=0.4:alpha=1,fade=t=out:st=$fo:d=0.4:alpha=1[lab];[v0][lab]overlay=0:0:eof_action=pass,format=yuv420p[v]"
  else
    filtro="$fv[v]"
  fi
  filtro="$filtro;[1:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,apad[a]"
  ffmpeg "${args[@]}" -filter_complex "$filtro" -map "[v]" -map "[a]" -t "$dur" \
    -c:v libx264 -preset medium -crf 20 -r 30 -pix_fmt yuv420p -color_range tv \
    -c:a aac -b:a 160k -ar 48000 -ac 2 -movflags +faststart "$out"
  printf '  %-34s %6.1f s%s\n' "$(basename "$out")" "$dur" "$( awk -v p="$pad" 'BEGIN { if (p > 0.001) printf "  (último quadro congelado por %.1f s)", p }')"
}

# ---------- montagem ----------
: > "$TMP/lista.txt"
i=0
echo "Montando em $TMP"
if [ -n "$INTRO_ARQ" ] && [ -f "$INTRO_ARQ" ]; then
  fala0="$(achar "$GRAVACOES/fala00" m4a wav mp3 aac || true)"
  [ -n "$fala0" ] || aviso "sem fala00.m4a: a abertura fica sem narração"
  segmento "$INTRO_ARQ" "$fala0" "" "00" "$TMP/seg000.mp4"
  echo "file '$TMP/seg000.mp4'" >> "$TMP/lista.txt"
fi
for idx in "${!NUMS[@]}"; do
  n="${NUMS[$idx]}"; t="${TITULOS[$idx]}"
  v="$(achar "$GRAVACOES/cena$n" mov mp4 m4v || true)"
  [ -n "$v" ] || { aviso "cena $n sem gravação: pulada"; continue; }
  a="$(achar "$GRAVACOES/fala$n" m4a wav mp3 aac || true)"
  i=$((i + 1))
  segmento "$v" "$a" "$t" "$n" "$TMP/seg$(printf %03d $((idx + 1))).mp4"
  echo "file '$TMP/seg$(printf %03d $((idx + 1))).mp4'" >> "$TMP/lista.txt"
done
[ -s "$TMP/lista.txt" ] || erro "nada para montar"

mkdir -p "$(dirname "$SAIDA")"
ffmpeg -y -v error -f concat -safe 0 -i "$TMP/lista.txt" -c copy -movflags +faststart "$SAIDA"
echo
echo "Pronto: $SAIDA"
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,sample_rate,channels -of default=nw=1 "$SAIDA"
