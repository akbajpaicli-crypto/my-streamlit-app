import argparse
import math
from collections import defaultdict

import pandas as pd


def haversine_meters(lat1, lon1, lat2, lon2):
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


class GridIndex:
    def __init__(self, grid_deg=0.001):
        self.grid = defaultdict(list)
        self.grid_deg = grid_deg

    def _cell(self, lat, lon):
        return (int(lat / self.grid_deg), int(lon / self.grid_deg))

    def insert(self, idx, lat, lon):
        self.grid[self._cell(lat, lon)].append((idx, lat, lon))

    def query(self, lat, lon):
        cx, cy = self._cell(lat, lon)
        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                candidates.extend(self.grid.get((cx + dx, cy + dy), []))
        return candidates


def find_columns(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None


def pick_nearest(ohe_csv, rtis_csv, out_csv, section='ET-JBP', max_dist_m=50.0, grid_deg=0.001):
    df_p = pd.read_csv(ohe_csv)
    sec_col = find_columns(df_p, ['SectionID','section','Section'])
    # If there is no SectionID column, operate on the whole OHE CSV
    if sec_col is None:
        df_section = df_p.copy()
    else:
        # If a specific section was provided, filter; otherwise use all rows
        if section is None:
            df_section = df_p.copy()
        else:
            df_section = df_p[df_p[sec_col].astype(str) == str(section)].copy()
            if df_section.empty:
                raise SystemExit(f'No poles for section {section}')

    plat = find_columns(df_section, ['Latitude','latitude','lat'])
    plon = find_columns(df_section, ['Longitude','longitude','lon'])
    label = find_columns(df_section, ['OHEMas','OHE','pole','pole_label']) or 'OHEMas'
    if plat is None or plon is None:
        raise SystemExit('Latitude/Longitude columns not found in OHE CSV')

    df_r = pd.read_csv(rtis_csv)
    rlat = find_columns(df_r, ['Latitude','latitude','lat'])
    rlon = find_columns(df_r, ['Longitude','longitude','lon'])
    rtime = find_columns(df_r, ['Logging Time','LoggingTime','ModifiedDate','logging_time','timestamp'])
    rspeed = find_columns(df_r, ['Speed','speed','speed_kmph'])
    if rlat is None or rlon is None:
        raise SystemExit('Latitude/Longitude columns not found in RTIS CSV')

    # build RTIS grid index
    rtis_points = []
    gi = GridIndex(grid_deg=grid_deg)
    for i, r in df_r.iterrows():
        try:
            lat = float(r[rlat])
            lon = float(r[rlon])
        except Exception:
            continue
        rtis_points.append(r)
        gi.insert(i, lat, lon)

    results = []
    for _, p in df_section.iterrows():
        try:
            plat_v = float(p[plat])
            plon_v = float(p[plon])
        except Exception:
            continue
        # find candidate RTIS nearby
        cand = gi.query(plat_v, plon_v)
        best = None
        best_dist = float('inf')
        for idx, latc, lonc in cand:
            d = haversine_meters(plat_v, plon_v, latc, lonc)
            if d < best_dist:
                best_dist = d
                best = idx
        if best is not None and best_dist <= max_dist_m:
            r = df_r.loc[best]
            time_val = str(r[rtime]) if rtime in df_r.columns else ''
            speed_val = float(r[rspeed]) if (rspeed in df_r.columns and pd.notna(r[rspeed])) else ''
            label_v = str(p[label]) if label in df_section.columns else ''
            results.append({'OHEMas': label_v, 'logging_time': time_val, 'speed_kmph': speed_val})
        else:
            label_v = str(p[label]) if label in df_section.columns else ''
            results.append({'OHEMas': label_v, 'logging_time': '', 'speed_kmph': ''})

    out_df = pd.DataFrame(results)
    out_df.to_csv(out_csv, index=False)
    return out_df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ohe_csv')
    ap.add_argument('rtis_csv')
    ap.add_argument('out_csv')
    ap.add_argument('--section', default=None)
    ap.add_argument('--max-dist-m', type=float, default=50.0)
    ap.add_argument('--grid-deg', type=float, default=0.001)
    args = ap.parse_args()
    df = pick_nearest(args.ohe_csv, args.rtis_csv, args.out_csv, section=args.section, max_dist_m=args.max_dist_m, grid_deg=args.grid_deg)
    print('wrote', args.out_csv, 'rows:', len(df))


if __name__ == '__main__':
    import argparse
    main()
