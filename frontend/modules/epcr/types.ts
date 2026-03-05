/**
 * ePCR module types.
 */

export type ePCRStatus = 'DRAFT' | 'IN_PROGRESS' | 'COMPLETED' | 'LOCKED' | 'EXPORTED';

export interface ePCRRecord {
  id: string;
  incidentId: string;
  patientName: string;
  status: ePCRStatus;
  createdAt: string;
  updatedAt: string;
  crew: string[];
}
