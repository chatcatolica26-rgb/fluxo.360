"""Acesso a bases de dados de vídeo e avaliação (independente dos algoritmos)."""
from .mot20_annotations import (DISTRACTOR_CLASSES, PEDESTRIAN, AnnotationFormatError, GroundTruth,
                                MOTAnnotations, annotations_from_records, load_ground_truth,
                                read_mot_file, write_mot_results, xywh_to_xyxy, xyxy_to_xywh)
from .mot20_loader import (PRIORITY_SEQUENCES, SEQUENCES, TEST_SEQUENCES, TRAIN_SEQUENCES,
                           DatasetNotFoundError, MOT20Dataset, SequenceInfo, read_seqinfo)
from .evaluation import (clear_metrics, counting_metrics, detection_metrics, evaluate_sequence,
                         hota_metrics, identity_metrics, iou_matrix, remove_distractor_matches,
                         save_metrics)

__all__ = [n for n in dir() if not n.startswith("_")]
