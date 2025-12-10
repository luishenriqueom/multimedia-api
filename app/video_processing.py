import ffmpeg
import io
import tempfile
import os
from typing import Dict, Optional, Tuple
from PIL import Image


def extract_video_metadata(video_bytes: bytes) -> Dict:
    """Extrai metadados de um vídeo usando ffmpeg.
    
    Returns:
        Dict com as seguintes chaves:
        - duration_seconds: float
        - width: int
        - height: int
        - frame_rate: float
        - video_codec: str
        - audio_codec: str
        - bitrate: int (em bps)
    """
    metadata = {
        'duration_seconds': None,
        'width': None,
        'height': None,
        'frame_rate': None,
        'video_codec': None,
        'audio_codec': None,
        'bitrate': None
    }
    
    try:
        # Criar arquivo temporário para o vídeo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            tmp_file.write(video_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Usar ffmpeg.probe para extrair metadados
            probe = ffmpeg.probe(tmp_path)
            format_info = probe.get('format', {})
            streams = probe.get('streams', [])
            
            # Duração
            duration = format_info.get('duration')
            if duration:
                metadata['duration_seconds'] = float(duration)
            
            # Bitrate total
            bitrate = format_info.get('bit_rate')
            if bitrate:
                metadata['bitrate'] = int(bitrate)
            
            # Encontrar stream de vídeo
            video_stream = next((s for s in streams if s.get('codec_type') == 'video'), None)
            if video_stream:
                metadata['width'] = video_stream.get('width')
                metadata['height'] = video_stream.get('height')
                metadata['video_codec'] = video_stream.get('codec_name')
                
                # Calcular FPS
                avg_frame_rate = video_stream.get('avg_frame_rate', '0/0')
                if '/' in avg_frame_rate:
                    num, den = map(int, avg_frame_rate.split('/'))
                    if den > 0:
                        metadata['frame_rate'] = num / den
            
            # Encontrar stream de áudio
            audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            if audio_stream:
                metadata['audio_codec'] = audio_stream.get('codec_name')
        
        finally:
            # Remover arquivo temporário
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        # Em caso de erro, retornar metadados parciais
        print(f"Erro ao extrair metadados do vídeo: {e}")
    
    return metadata


def generate_video_thumbnail(video_bytes: bytes, timestamp: float = 1.0) -> Optional[io.BytesIO]:
    """Gera uma thumbnail do vídeo no timestamp especificado.
    
    Args:
        video_bytes: Bytes do vídeo
        timestamp: Segundo do vídeo para capturar (padrão: 1.0)
    
    Returns:
        BytesIO com a imagem JPEG da thumbnail, ou None em caso de erro
    """
    try:
        # Criar arquivo temporário para o vídeo
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_video:
            tmp_video.write(video_bytes)
            tmp_video_path = tmp_video.name
        
        # Criar arquivo temporário para a thumbnail
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_thumb:
            tmp_thumb_path = tmp_thumb.name
        
        try:
            # Usar ffmpeg para extrair frame e redimensionar
            (
                ffmpeg
                .input(tmp_video_path, ss=timestamp)
                .filter('scale', 320, -1)
                .output(tmp_thumb_path, vframes=1, loglevel="error")
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            # Ler a thumbnail gerada
            with open(tmp_thumb_path, 'rb') as f:
                thumb_bytes = f.read()
            
            thumb_io = io.BytesIO(thumb_bytes)
            thumb_io.seek(0)
            return thumb_io
        
        finally:
            # Remover arquivos temporários
            if os.path.exists(tmp_video_path):
                os.unlink(tmp_video_path)
            if os.path.exists(tmp_thumb_path):
                os.unlink(tmp_thumb_path)
    
    except Exception as e:
        print(f"Erro ao gerar thumbnail: {e}")
        return None


def generate_video_rendition(video_bytes: bytes, target_height: int, bitrate: str = None) -> Optional[io.BytesIO]:
    """Gera uma versão do vídeo com a altura especificada.
    
    Args:
        video_bytes: Bytes do vídeo original
        target_height: Altura alvo (480, 720, 1080)
        bitrate: Bitrate alvo (ex: '2M' para 2Mbps). Se None, usa valores padrão baseados na resolução
    
    Returns:
        BytesIO com o vídeo processado, ou None em caso de erro
    """
    if bitrate is None:
        # Bitrates padrão baseados na resolução
        bitrate_map = {
            480: '1M',
            720: '2.5M',
            1080: '5M'
        }
        bitrate = bitrate_map.get(target_height, '2M')
    
    try:
        # Criar arquivo temporário para o vídeo de entrada
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_input:
            tmp_input.write(video_bytes)
            tmp_input_path = tmp_input.name
        
        # Criar arquivo temporário para o vídeo de saída
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_output:
            tmp_output_path = tmp_output.name
        
        try:
            # Verificar se o vídeo tem áudio usando ffmpeg.probe
            probe = ffmpeg.probe(tmp_input_path)
            has_audio = any(stream.get('codec_type') == 'audio' for stream in probe.get('streams', []))
            
            # Usar ffmpeg para transcodificar
            # Escala mantendo aspect ratio, ajusta bitrate e usa codec H.264
            # Mapeia explicitamente os streams de vídeo e áudio para garantir que o áudio seja preservado
            input_stream = ffmpeg.input(tmp_input_path)
            
            # Aplicar filtro de escala apenas ao stream de vídeo
            video_stream = input_stream['v'].filter('scale', -1, target_height)
            
            # Configurar parâmetros de output
            output_kwargs = {
                'vcodec': 'libx264',
                **{'b:v': bitrate},  # Bitrate de vídeo
                'preset': 'medium',
                'movflags': 'faststart',  # Otimiza para streaming
                'loglevel': 'error'
            }
            
            # Adicionar áudio apenas se existir no vídeo original
            if has_audio:
                audio_stream = input_stream['a']
                output_kwargs['acodec'] = 'aac'
                output_kwargs['b:a'] = '128k'
                (
                    ffmpeg
                    .output(video_stream, audio_stream, tmp_output_path, **output_kwargs)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            else:
                # Vídeo sem áudio
                (
                    ffmpeg
                    .output(video_stream, tmp_output_path, **output_kwargs)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            
            # Ler o vídeo processado
            with open(tmp_output_path, 'rb') as f:
                output_bytes = f.read()
            
            output_io = io.BytesIO(output_bytes)
            output_io.seek(0)
            return output_io
        
        finally:
            # Remover arquivos temporários
            if os.path.exists(tmp_input_path):
                os.unlink(tmp_input_path)
            if os.path.exists(tmp_output_path):
                os.unlink(tmp_output_path)
    
    except Exception as e:
        print(f"Erro ao gerar versão {target_height}p: {e}")
        return None


def get_thumbnail_dimensions(thumb_io: io.BytesIO) -> Tuple[Optional[int], Optional[int]]:
    """Obtém as dimensões de uma thumbnail.
    
    Returns:
        Tuple (width, height) ou (None, None) em caso de erro
    """
    try:
        thumb_io.seek(0)
        img = Image.open(thumb_io)
        return img.size
    except Exception as e:
        print(f"Erro ao obter dimensões da thumbnail: {e}")
        return (None, None)

