export interface Zone {
  id: string;
  nom: string;
  description?: string;
}

export interface Personne {
  id: string;
  nom: string;
  prenom?: string;
  email?: string;
  telephone?: string;
  role: string; // SURVEILLANT, DIRECTEUR, AGENT_DE_DIRECTION, PROF, ELEVE, PERSONNEL
  statut: string; // ACTIF / INACTIF
  creeLe: string;
  // embedding volontairement absent ici : jamais nécessaire côté interface,
  // et inutile d'alourdir chaque réponse HTTP avec 128/512 nombres
}

export interface RegleAcces {
  id: string;
  personneId: string;
  zoneId: string;
  horaireDebut: string; // "HH:mm:ss"
  horaireFin: string;
}

export interface Classe {
  id: string;
  nom: string;
  eleveIds: string[];
}

export interface Cours {
  id: string;
  nom: string;
  classeId: string;
  profId: string;
  zoneId: string;
  jourSemaine: 'LUNDI' | 'MARDI' | 'MERCREDI' | 'JEUDI' | 'VENDREDI' | 'SAMEDI';
  heureDebut: string; // "HH:mm:ss"
  heureFin: string;
}

export interface EvenementAcces {
  id: string;
  personneId: string | null;
  zoneId: string;
  horodatage: string;
  resultat: 'ACCORDE' | 'REFUSE';
  raison: string;
  capturePhoto?: string; // image encodée en base64 (data URI)
}

export interface Alerte {
  id: string;
  type: string; // SPOOFING, ACCES_NON_AUTORISE, ACCES_INTERDIT, HORAIRE_INTERDIT, PRESENCE_NON_IDENTIFIEE, IDENTITE_A_CONFIRMER
  evenementId: string;
  statut: 'NON_TRAITEE' | 'TRAITEE';
  horodatage: string;
  commentaireTraitement?: string;
  traitePar?: string;
  dateTraitement?: string;
  capturePhoto?: string; // image encodée en base64 (data URI), capturée au moment de l'alerte
}

export interface AccessDecision {
  personneId: string | null;
  nom: string | null;
  zoneId: string;
  resultat: 'ACCORDE' | 'REFUSE';
  raison: string;
}