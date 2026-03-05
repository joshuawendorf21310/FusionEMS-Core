/**
 * Fleet module types.
 */

export type VehicleStatus = 'IN_SERVICE' | 'OUT_OF_SERVICE' | 'MAINTENANCE' | 'RESERVE';

export interface Vehicle {
  id: string;
  unitNumber: string;
  type: string;
  status: VehicleStatus;
  mileage: number;
  lastInspection: string | null;
  assignedStation: string | null;
}
