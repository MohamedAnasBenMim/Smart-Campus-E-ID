export interface PresenceIndividuelle {
  personneId: string;
  statut: 'PRESENT' | 'ABSENT' | 'RETARD';
  heureArrivee: string | null;
}

export interface PresenceCours {
  id?: string;
  coursId: string;
  date: string; // "YYYY-MM-DD"
  presencesEleves: PresenceIndividuelle[];
  presenceProf: PresenceIndividuelle;
  statutSeance: 'PREREMPLIE' | 'VALIDEE';
  marqueePar?: string;
  dateMarquage?: string;
}