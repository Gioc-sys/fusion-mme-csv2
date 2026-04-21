import os
import csv
import shutil
import zipfile
import py7zr
from io import BytesIO, StringIO
from typing import Dict, List, Tuple


class ProcessingStats:
    """Statistiques de traitement"""
    def __init__(self):
        self.channels_added = 0
        self.files_merged = 0
        self.total_channels = 0
        self.samples_processed = 0
        self.errors = []
    
    def to_dict(self) -> Dict:
        return {
            'channelsAdded': self.channels_added,
            'filesMerged': self.files_merged,
            'totalChannels': self.total_channels,
            'samplesProcessed': self.samples_processed,
            'errors': self.errors
        }


class MMEProcessor:
    """Processeur pour les fichiers MME"""
    
    @staticmethod
    def extract_archive(archive_path: str, extract_to: str) -> str:
        """Extraire une archive ZIP ou 7Z"""
        if archive_path.lower().endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif archive_path.lower().endswith('.7z'):
            with py7zr.SevenZipFile(archive_path, mode='r') as z:
                z.extractall(path=extract_to)
        else:
            raise ValueError(f"Format d'archive non supporté: {archive_path}")
        
        # Trouver le dossier racine extrait
        items = os.listdir(extract_to)
        if len(items) == 1 and os.path.isdir(os.path.join(extract_to, items[0])):
            return os.path.join(extract_to, items[0])
        return extract_to
    
    @staticmethod
    def find_file_by_extension(directory: str, extension: str) -> str:
        """Trouver un fichier par extension dans un répertoire"""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.upper().endswith(extension.upper()):
                    return os.path.join(root, file)
        return None
    
    @staticmethod
    def find_channel_folder(mme_dir: str) -> str:
        """Trouver le dossier CHANNEL"""
        for root, dirs, files in os.walk(mme_dir):
            for dir_name in dirs:
                if dir_name.upper() == 'CHANNEL':
                    return os.path.join(root, dir_name)
        return None
    
    @staticmethod
    def read_chn_file(chn_path: str) -> Dict:
        """Lire un fichier .CHN et extraire les informations"""
        channels = []
        num_channels = 0
        
        with open(chn_path, 'r', encoding='latin-1', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if line.startswith('Number of channels'):
                    parts = line.split(':')
                    if len(parts) > 1:
                        num_channels = int(parts[1].strip())
                elif line.startswith('Name of channel'):
                    # Extraire le numéro et le nom
                    parts = line.split(':')
                    if len(parts) > 1:
                        channel_info = parts[1].strip()
                        channels.append(channel_info)
        
        return {
            'num_channels': num_channels,
            'channels': channels
        }
    
    @staticmethod
    def write_chn_file(chn_path: str, channels_info: List[str], num_channels: int):
        """Écrire un fichier .CHN mis à jour"""
        lines = []
        lines.append("Instrumentation standard    :SAE J211 / ISO 6487\r\n")
        lines.append(f"Number of channels          :{num_channels}\r\n")
        
        for i, channel_info in enumerate(channels_info, 1):
            lines.append(f"Name of channel {i:03d}         :{channel_info}\r\n")
        
        with open(chn_path, 'w', encoding='latin-1') as f:
            f.writelines(lines)
    
    @staticmethod
    def find_csv_column(csv_path: str, column_name: str) -> Tuple[int, List[str]]:
        """Trouver une colonne dans le CSV et retourner son index et ses valeurs"""
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Trouver la ligne d'en-tête avec le nom de la colonne
            header_line_idx = -1
            for i, line in enumerate(lines):
                if column_name in line:
                    header_line_idx = i
                    break
            
            if header_line_idx == -1:
                raise ValueError(f"Colonne '{column_name}' non trouvée dans le CSV")
            
            # Parser l'en-tête
            header_line = lines[header_line_idx]
            headers = header_line.split(';')
            
            # Trouver l'index de la colonne
            col_idx = -1
            for i, h in enumerate(headers):
                if column_name in h:
                    col_idx = i
                    break
            
            if col_idx == -1:
                raise ValueError(f"Colonne '{column_name}' non trouvée dans l'en-tête")
            
            # Extraire les valeurs (lignes suivantes)
            values = []
            for line in lines[header_line_idx + 1:]:
                if line.strip():
                    parts = line.split(';')
                    if len(parts) > col_idx:
                        value = parts[col_idx].strip()
                        if value:
                            values.append(value)
            
            return col_idx, values
    
    @staticmethod
    def create_channel_file(channel_path: str, values: List[str], channel_name: str):
        """Créer un fichier de canal (.001, .002, etc.) à partir des valeurs CSV"""
        # Format binaire simple pour les channels MME
        # Structure: en-tête + données
        
        with open(channel_path, 'wb') as f:
            # En-tête simplifié (à adapter selon le format exact MME)
            header = f"Channel: {channel_name}\n".encode('latin-1')
            f.write(header)
            
            # Écrire les valeurs
            for value in values:
                try:
                    # Convertir en float et écrire en binaire
                    float_val = float(value)
                    f.write(float_val.to_bytes(8, byteorder='little', signed=True))
                except:
                    # Si conversion échoue, écrire 0
                    f.write((0).to_bytes(8, byteorder='little', signed=True))
    
    def add_csv_channels(self, mme_archive_path: str, csv_path: str, settings: Dict) -> Tuple[bytes, Dict]:
        """Ajouter des voies CSV à un fichier MME"""
        stats = ProcessingStats()
        temp_dir = None
        
        try:
            import tempfile
            temp_dir = tempfile.mkdtemp()
            
            # Extraire l'archive MME
            mme_dir = self.extract_archive(mme_archive_path, temp_dir)
            
            # Trouver le dossier CHANNEL
            channel_dir = self.find_channel_folder(mme_dir)
            if not channel_dir:
                raise ValueError("Dossier CHANNEL non trouvé dans l'archive MME")
            
            # Trouver le fichier .CHN
            chn_file = None
            for file in os.listdir(channel_dir):
                if file.upper().endswith('.CHN'):
                    chn_file = os.path.join(channel_dir, file)
                    break
            
            if not chn_file:
                raise ValueError("Fichier .CHN non trouvé")
            
            # Lire les informations des channels existants
            chn_info = self.read_chn_file(chn_file)
            current_num_channels = chn_info['num_channels']
            channels_list = chn_info['channels']
            
            # Extraire le nom de base des fichiers (ex: CINV_2294)
            base_name = os.path.basename(channel_dir).replace('CHANNEL', '').strip()
            if not base_name:
                # Chercher dans les fichiers existants
                for file in os.listdir(channel_dir):
                    if '.' in file and not file.endswith('.CHN'):
                        base_name = file.split('.')[0]
                        break
            
            # Traiter Head Rebound Velocity
            try:
                col_idx, head_values = self.find_csv_column(csv_path, settings['csvHeadVelocityColumn'])
                next_channel_num = current_num_channels + 1
                channel_file_path = os.path.join(channel_dir, f"{base_name}.{next_channel_num:03d}")
                
                self.create_channel_file(channel_file_path, head_values, settings['headVelocityName'])
                channels_list.append(f"{settings['mmeHeadVelocityChannel']} / {settings['headVelocityName']}")
                current_num_channels += 1
                stats.channels_added += 1
                stats.samples_processed += len(head_values)
            except Exception as e:
                stats.errors.append(f"Head Velocity: {str(e)}")
            
            # Traiter Seatback Deflection
            try:
                col_idx, seat_values = self.find_csv_column(csv_path, settings['csvSeatbackColumn'])
                next_channel_num = current_num_channels + 1
                channel_file_path = os.path.join(channel_dir, f"{base_name}.{next_channel_num:03d}")
                
                self.create_channel_file(channel_file_path, seat_values, settings['seatbackName'])
                channels_list.append(f"{settings['mmeSeatbackChannel']} / {settings['seatbackName']}")
                current_num_channels += 1
                stats.channels_added += 1
                stats.samples_processed += len(seat_values)
            except Exception as e:
                stats.errors.append(f"Seatback Deflection: {str(e)}")
            
            # Mettre à jour le fichier .CHN
            self.write_chn_file(chn_file, channels_list, current_num_channels)
            stats.total_channels = current_num_channels
            
            # Créer l'archive de résultat
            output_buffer = BytesIO()
            with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(mme_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(mme_dir))
                        zipf.write(file_path, arcname)
            
            return output_buffer.getvalue(), stats.to_dict()
            
        except Exception as e:
            stats.errors.append(f"Erreur générale: {str(e)}")
            raise e
        
        finally:
            # Nettoyer
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
    
    def merge_mme_files(self, mme_archive_paths: List[str]) -> Tuple[bytes, Dict]:
        """Fusionner plusieurs fichiers MME"""
        stats = ProcessingStats()
        temp_dir = None
        
        try:
            import tempfile
            temp_dir = tempfile.mkdtemp()
            
            # Extraire le premier MME comme base
            base_mme_dir = self.extract_archive(mme_archive_paths[0], os.path.join(temp_dir, 'base'))
            base_channel_dir = self.find_channel_folder(base_mme_dir)
            
            if not base_channel_dir:
                raise ValueError("Dossier CHANNEL non trouvé dans le premier fichier MME")
            
            # Trouver le fichier .CHN
            base_chn_file = None
            for file in os.listdir(base_channel_dir):
                if file.upper().endswith('.CHN'):
                    base_chn_file = os.path.join(base_channel_dir, file)
                    break
            
            if not base_chn_file:
                raise ValueError("Fichier .CHN non trouvé dans le premier fichier MME")
            
            # Lire les channels existants
            chn_info = self.read_chn_file(base_chn_file)
            current_num_channels = chn_info['num_channels']
            channels_list = chn_info['channels']
            
            # Extraire le nom de base
            base_name = None
            for file in os.listdir(base_channel_dir):
                if '.' in file and not file.endswith('.CHN'):
                    base_name = file.split('.')[0]
                    break
            
            if not base_name:
                base_name = os.path.basename(base_channel_dir)
            
            stats.files_merged = 1
            
            # Fusionner les autres fichiers
            for i, archive_path in enumerate(mme_archive_paths[1:], 2):
                try:
                    # Extraire le MME suivant
                    mme_dir = self.extract_archive(archive_path, os.path.join(temp_dir, f'mme_{i}'))
                    channel_dir = self.find_channel_folder(mme_dir)
                    
                    if not channel_dir:
                        stats.errors.append(f"Fichier {i}: Dossier CHANNEL non trouvé")
                        continue
                    
                    # Lire les channels de ce fichier
                    chn_file = None
                    for file in os.listdir(channel_dir):
                        if file.upper().endswith('.CHN'):
                            chn_file = os.path.join(channel_dir, file)
                            break
                    
                    if not chn_file:
                        stats.errors.append(f"Fichier {i}: .CHN non trouvé")
                        continue
                    
                    merge_chn_info = self.read_chn_file(chn_file)
                    
                    # Copier les fichiers de channel en incrémentant le numéro
                    for file in os.listdir(channel_dir):
                        if file.upper().endswith('.CHN'):
                            continue
                        
                        # Extraire le numéro d'extension
                        if '.' in file:
                            parts = file.split('.')
                            if len(parts) == 2 and parts[1].isdigit():
                                current_num_channels += 1
                                new_filename = f"{base_name}.{current_num_channels:03d}"
                                src = os.path.join(channel_dir, file)
                                dst = os.path.join(base_channel_dir, new_filename)
                                shutil.copy2(src, dst)
                    
                    # Ajouter les noms de channels
                    channels_list.extend(merge_chn_info['channels'])
                    stats.files_merged += 1
                    
                except Exception as e:
                    stats.errors.append(f"Fichier {i}: {str(e)}")
            
            # Mettre à jour le .CHN
            stats.total_channels = current_num_channels
            self.write_chn_file(base_chn_file, channels_list, current_num_channels)
            
            # Créer l'archive de résultat
            output_buffer = BytesIO()
            with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(base_mme_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(base_mme_dir))
                        zipf.write(file_path, arcname)
            
            return output_buffer.getvalue(), stats.to_dict()
            
        except Exception as e:
            stats.errors.append(f"Erreur générale: {str(e)}")
            raise e
        
        finally:
            # Nettoyer
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
