import ffmpeg
import io
import tempfile
import os
from typing import Dict, Optional
import soundfile as sf


def extract_audio_metadata(audio_bytes: bytes) -> Dict:
    """Extrai metadados de um arquivo de áudio usando soundfile (com fallback para ffmpeg).
    
    Returns:
        Dict com as seguintes chaves:
        - duration_seconds: float
        - bitrate: int (em bps)
        - sample_rate: int (em Hz)
        - channels: int
    """
    metadata = {
        'duration_seconds': None,
        'bitrate': None,
        'sample_rate': None,
        'channels': None
    }
    
    try:
        # Criar arquivo temporário para o áudio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        try:
            # Tentar usar soundfile primeiro (excelente para WAV/FLAC)
            try:
                info = sf.info(tmp_path)
                metadata['duration_seconds'] = float(info.duration)
                metadata['sample_rate'] = int(info.samplerate)
                metadata['channels'] = int(info.channels)
                
                # Calcular bitrate estimado: (tamanho_bytes * 8) / duração
                size_bits = len(audio_bytes) * 8
                if metadata['duration_seconds'] and metadata['duration_seconds'] > 0:
                    metadata['bitrate'] = int(size_bits / metadata['duration_seconds'])
            
            except Exception as sf_error:
                # Fallback para ffmpeg se soundfile falhar (ex: alguns MP3s)
                print(f"Soundfile falhou, usando ffmpeg como fallback: {sf_error}")
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
                
                # Encontrar stream de áudio
                audio_stream = next((s for s in streams if s.get('codec_type') == 'audio'), None)
                if audio_stream:
                    sample_rate = audio_stream.get('sample_rate')
                    if sample_rate:
                        metadata['sample_rate'] = int(sample_rate)
                    
                    channels = audio_stream.get('channels')
                    if channels:
                        metadata['channels'] = int(channels)
                    
                    # Se não tiver bitrate do formato, tentar calcular
                    if not metadata['bitrate'] and metadata['duration_seconds'] and metadata['duration_seconds'] > 0:
                        size_bits = len(audio_bytes) * 8
                        metadata['bitrate'] = int(size_bits / metadata['duration_seconds'])
        
        finally:
            # Remover arquivo temporário
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    except Exception as e:
        # Em caso de erro, retornar metadados parciais
        print(f"Erro ao extrair metadados do áudio: {e}")
    
    return metadata

