"use client";

import "leaflet/dist/leaflet.css";
import { LatLngBoundsExpression } from "leaflet";
import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";

type MapPoint = {
  label: string;
  severity: number;
  directness: string;
  lat: number;
  lon: number;
};

type ImpactMapProps = {
  points: MapPoint[];
  lensType: "global" | "region" | "country";
  lensFocus: string;
};

const REGION_VIEW: Record<string, { center: [number, number]; zoom: number }> = {
  Gulf: { center: [25.5, 51.0], zoom: 4 },
  Levant: { center: [33.5, 36.0], zoom: 5 },
  MENA: { center: [28.5, 38.0], zoom: 4 },
  Europe: { center: [52.0, 12.0], zoom: 4 },
  "East Asia": { center: [30.0, 122.0], zoom: 4 },
  "Global shipping lanes": { center: [19.0, 40.0], zoom: 3 },
};

function severityColor(value: number): string {
  if (value >= 0.8) {
    return "#ef4444";
  }
  if (value >= 0.6) {
    return "#f97316";
  }
  if (value >= 0.4) {
    return "#f59e0b";
  }
  if (value >= 0.2) {
    return "#84cc16";
  }
  return "#22c55e";
}

function boundsFromPoints(points: MapPoint[]): LatLngBoundsExpression | null {
  if (points.length === 0) {
    return null;
  }
  const lats = points.map((p) => p.lat);
  const lons = points.map((p) => p.lon);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const latPad = Math.max((maxLat - minLat) * 0.35, 4);
  const lonPad = Math.max((maxLon - minLon) * 0.35, 6);
  return [
    [minLat - latPad, minLon - lonPad],
    [maxLat + latPad, maxLon + lonPad],
  ];
}

export default function ImpactMap({ points, lensType, lensFocus }: ImpactMapProps) {
  const pointBounds = boundsFromPoints(points);
  const regionPreset = REGION_VIEW[lensFocus];
  const defaultCenter: [number, number] = [20, 10];
  const defaultZoom = lensType === "global" ? 2 : 3;
  const mapKey = `${lensType}:${lensFocus}:${points.map((p) => `${p.label}-${p.lat}-${p.lon}`).join("|")}`;

  return (
    <MapContainer
      key={mapKey}
      className="country-map"
      center={regionPreset?.center ?? defaultCenter}
      zoom={regionPreset?.zoom ?? defaultZoom}
      bounds={lensType === "global" && points.length === 0 ? undefined : pointBounds ?? undefined}
      worldCopyJump
      scrollWheelZoom={false}
      zoomControl
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {points.map((point) => (
        <CircleMarker
          key={`${point.label}-${point.lat}-${point.lon}`}
          center={[point.lat, point.lon]}
          radius={point.directness === "direct" ? 8 : 6}
          pathOptions={{ color: "#e2e8f0", weight: 1, fillColor: severityColor(point.severity), fillOpacity: 0.9 }}
        >
          <Tooltip permanent direction="top" offset={[0, -10]} opacity={0.9}>
            {point.label}
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
