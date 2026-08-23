export interface RegleAccesRole {
  id: string;
  role: string;
  zoneId: string;
  horaireDebut: string; // "HH:mm:ss"
  horaireFin: string;
}