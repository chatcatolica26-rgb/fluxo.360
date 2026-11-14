"""Projeção câmera -> planta via homografia do piso."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import cv2
import yaml


@dataclass
class CameraPlanta:
    camera_id: str
    piso: str
    H: np.ndarray                 # 3x3, pixel do vídeo -> pixel da planta
    px_por_metro: float
    mascara: np.ndarray | None = None   # uint8 (altura x largura da planta), 255 = área válida

    @classmethod
    def carregar(cls, cam_yaml: str | Path, planta_yaml: str | Path = "configs/planta.yaml",
                 raiz: str | Path = ".") -> "CameraPlanta":
        cam = yaml.safe_load(Path(cam_yaml).read_text(encoding="utf-8"))
        planta = yaml.safe_load(Path(planta_yaml).read_text(encoding="utf-8"))
        piso = planta["pisos"][cam["piso"]]
        mascara = None
        if cam.get("mascara"):
            mascara = cv2.imread(str(Path(raiz) / cam["mascara"]), cv2.IMREAD_GRAYSCALE)
        return cls(cam["camera_id"], cam["piso"], np.array(cam["H"], dtype=np.float64),
                   float(piso["px_por_metro"]), mascara)

    def projetar(self, pts_video: np.ndarray) -> np.ndarray:
        """pts_video: (N,2) em pixels do vídeo -> (N,2) em pixels da planta."""
        pts = np.asarray(pts_video, dtype=np.float64).reshape(-1, 1, 2)
        if len(pts) == 0:
            return np.empty((0, 2))
        return cv2.perspectiveTransform(pts, self.H).reshape(-1, 2)

    def projetar_caixas(self, caixas_xyxy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Usa o ponto dos pés (centro da borda inferior). Retorna (pontos_planta, validos)."""
        c = np.asarray(caixas_xyxy, dtype=np.float64).reshape(-1, 4)
        pes = np.stack([(c[:, 0] + c[:, 2]) / 2, c[:, 3]], axis=1)
        p = self.projetar(pes)
        return p, self.dentro(p)

    def dentro(self, p: np.ndarray) -> np.ndarray:
        if self.mascara is None:
            return np.ones(len(p), dtype=bool)
        h, w = self.mascara.shape
        xi, yi = np.round(p[:, 0]).astype(int), np.round(p[:, 1]).astype(int)
        ok = (xi >= 0) & (xi < w) & (yi >= 0) & (yi < h)
        ok[ok] = self.mascara[yi[ok], xi[ok]] > 0
        return ok

    def em_metros(self, p_planta: np.ndarray) -> np.ndarray:
        return np.asarray(p_planta) / self.px_por_metro
