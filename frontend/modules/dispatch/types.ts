/**
 * Dispatch module types.
 *
 * These types are shared across all dispatch-related components and services.
 */

export type UnitStatus =
  | 'AVAILABLE'
  | 'DISPATCHED'
  | 'EN_ROUTE'
  | 'ON_SCENE'
  | 'TRANSPORTING'
  | 'AT_HOSPITAL'
  | 'OUT_OF_SERVICE';

export interface DispatchUnit {
  id: string;
  callSign: string;
  status: UnitStatus;
  lat: number | null;
  lng: number | null;
  crew: string[];
  assignedIncidentId: string | null;
  lastStatusChange: string;
}

export type IncidentPriority = 'ALPHA' | 'BRAVO' | 'CHARLIE' | 'DELTA' | 'ECHO' | 'OMEGA';

export interface Incident {
  id: string;
  caseNumber: string;
  priority: IncidentPriority;
  nature: string;
  address: string;
  lat: number;
  lng: number;
  dispatchTime: string;
  assignedUnits: string[];
  status: string;
}

export interface DispatchState {
  units: DispatchUnit[];
  incidents: Incident[];
  selectedUnitId: string | null;
  selectedIncidentId: string | null;
}
