import argparse
import json
import math
from datetime import datetime, timezone
import cv2

# Zone geometry as fractions of the frame (tuned to the supplied street video)
XING = (0.20, 0.85, 0.73, 0.94)      # crosswalk box: x0, y0, x1, y1
STOP_Y = 0.845                      # stop-line / counting line
MIN_AREA, MAX_DIST, MAX_MISS = 0.0025, 0.12, 12

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--out", default="crosssafe_annotated.mp4")
    ap.add_argument("--events", default="crosssafe_events.jsonl")
    ap.add_argument("--show", action="store_true")
    a = ap.parse_args()

    cap = cv2.VideoCapture(a.video)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    W, H = 960, 540
    vw = cv2.VideoWriter(a.out, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H))
    bg = cv2.createBackgroundSubtractorMOG2(history=120, varThreshold=40, detectShadows=False)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    tracks, nid, count, fr = {}, 1, 0, 0
    ev_f = open(a.events, "w")

    def emit(ev, tid, cx, cy, conf, act):
        e = {"site_id": "CROSSING_01", "event": ev, "track_id": tid, "class": "vehicle",
             "confidence": round(conf, 2), "position": {"x": round(cx * W), "y": round(cy * H)},
             "frame": fr, "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
             "action": act}
        ev_f.write(json.dumps(e) + "\n"); print(json.dumps(e))

    while True:
        ok, img = cap.read()
        if not ok:
            break
        fr += 1
        img = cv2.resize(img, (W, H))
        m = bg.apply(cv2.GaussianBlur(img, (5, 5), 0))
        m = cv2.morphologyEx(cv2.threshold(m, 200, 255, cv2.THRESH_BINARY)[1], cv2.MORPH_CLOSE, k)
        m = cv2.dilate(m, k, iterations=2)
        cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        dets = []
        if fr > 15:                         # let the background model warm up
            for c in cs:
                x, y, w, h = cv2.boundingRect(c)
                if w * h >= MIN_AREA * W * H and w > 25 and h > 20:
                    dets.append((x, y, w, h, min(.99, .5 + w * h / (W * H) * 4)))
        used = set()
        for tid, t in tracks.items():                # nearest-centroid association
            best, bd = None, MAX_DIST
            for i, d in enumerate(dets):
                if i in used:
                    continue
                dist = math.hypot((d[0] + d[2] / 2) / W - t["cx"], (d[1] + d[3]) / H - t["cy"])
                if dist < bd:
                    best, bd = i, dist
            if best is None:
                t["miss"] += 1
                continue
            used.add(best); d = dets[best]
            t.update(prev=t["cy"], cx=(d[0] + d[2] / 2) / W, cy=(d[1] + d[3]) / H, box=d[:4], conf=d[4], miss=0)
        for i, d in enumerate(dets):
            if i not in used:
                cy = (d[1] + d[3]) / H
                tracks[nid] = dict(cx=(d[0] + d[2] / 2) / W, cy=cy, prev=cy, box=d[:4], conf=d[4], miss=0, inz=False, ctd=False)
                nid += 1
        for tid in [t for t, v in tracks.items() if v["miss"] > MAX_MISS]:
            del tracks[tid]

        busy = False
        for tid, t in tracks.items():
            if t["miss"]:
                continue
            inz = XING[0] <= t["cx"] <= XING[2] and XING[1] <= t["cy"] <= XING[3]
            if inz and not t["inz"]:
                emit("CROSSWALK_OCCUPIED", tid, t["cx"], t["cy"], t["conf"], "ALERT_PEDESTRIANS")
            if t["prev"] < STOP_Y <= t["cy"] and not t["ctd"]:
                t["ctd"] = True; count += 1
                emit("LINE_CROSSED", tid, t["cx"], t["cy"], t["conf"], "COUNT_VEHICLE")
            t["inz"] = inz; busy |= inz
            x, y, w, h = t["box"]; col = (0, 0, 255) if inz else (0, 200, 0)
            cv2.rectangle(img, (x, y), (x + w, y + h), col, 2)
            cv2.putText(img, f"ID {tid} vehicle {t['conf']:.2f}", (x, max(14, y - 5)), 0, .5, col, 2)
        zc = (0, 0, 255) if busy else (0, 215, 255)
        cv2.rectangle(img, (int(XING[0] * W), int(XING[1] * H)), (int(XING[2] * W), int(XING[3] * H)), zc, 2)
        cv2.line(img, (0, int(STOP_Y * H)), (W, int(STOP_Y * H)), (255, 255, 0), 1)
        cv2.putText(img, f"CrossSafe  vehicles counted: {count}  crosswalk: {'OCCUPIED' if busy else 'CLEAR'}", (12, 28), 0, .7, (255, 255, 255), 2)
        vw.write(img)
        if a.show:
            cv2.imshow("CrossSafe", img)
            if cv2.waitKey(1) == 27:
                break
    print(f"done: {fr} frames, {count} line crossings -> {a.out}, {a.events}")

if __name__ == "__main__":
    main()