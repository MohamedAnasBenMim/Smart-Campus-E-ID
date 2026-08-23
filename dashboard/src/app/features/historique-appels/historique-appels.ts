import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatMenuModule } from '@angular/material/menu';
import { PresenceCoursService } from '../../core/services/presence-cours';
import { CoursService } from '../../core/services/cours';
import { ClassesService } from '../../core/services/classes';
import { Personnes as PersonnesService } from '../../core/services/personnes';
import { PresenceCours } from '../../core/models/presence';
import { Cours, Classe, Personne } from '../../core/models';

import * as XLSX from 'xlsx';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

interface LigneAppel {
  date: string;
  classeNom: string;
  coursNom: string;
  personneNom: string;
  role: string;
  statut: string;
  heureArrivee: string;
}

const LIBELLES_STATUT: Record<string, string> = {
  PRESENT: 'Présent',
  RETARD: 'Retard',
  ABSENT: 'Absent',
};

@Component({
  selector: 'app-historique-appels',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatIconModule,
    MatButtonModule,
    MatFormFieldModule,
    MatSelectModule,
    MatMenuModule,
  ],
  templateUrl: './historique-appels.html',
  styleUrl: './historique-appels.scss',
})
export class HistoriqueAppelsPage implements OnInit {
  presencesCours = signal<PresenceCours[]>([]);
  tousLesCours = signal<Cours[]>([]);
  classes = signal<Classe[]>([]);
  personnes = signal<Personne[]>([]);
  chargement = signal(true);

  classeFiltreId = signal<string>('TOUTES');
  dateDebut = signal<string>('');
  dateFin = signal<string>('');

  constructor(
    private presenceCoursService: PresenceCoursService,
    private coursService: CoursService,
    private classesService: ClassesService,
    private personnesService: PersonnesService,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.classesService.lister().subscribe((c) => this.classes.set(c));
    this.personnesService.lister().subscribe((p) => this.personnes.set(p));
    this.coursService.lister().subscribe((c) => this.tousLesCours.set(c));
    this.presenceCoursService.lister().subscribe({
      next: (presences) => {
        // Seuls les appels VALIDÉS ont un sens dans un historique.
        this.presencesCours.set(presences.filter((p) => p.statutSeance === 'VALIDEE'));
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  private nomPersonne(id: string): string {
    const p = this.personnes().find((x) => x.id === id);
    return p ? `${p.nom} ${p.prenom ?? ''}`.trim() : 'Inconnu';
  }

  private coursDe(id: string): Cours | undefined {
    return this.tousLesCours().find((c) => c.id === id);
  }

  private nomClasseDuCours(coursId: string): string {
    const cours = this.coursDe(coursId);
    if (!cours) return 'Classe inconnue';
    return this.classes().find((c) => c.id === cours.classeId)?.nom ?? 'Classe inconnue';
  }

  /**
   * Aplati chaque appel validé en plusieurs lignes (une par personne)
   * — format directement exploitable à l'écran ET à l'export, filtré
   * selon les critères sélectionnés.
   */
  lignes = computed<LigneAppel[]>(() => {
    const resultat: LigneAppel[] = [];

    for (const p of this.presencesCours()) {
      const cours = this.coursDe(p.coursId);
      if (!cours) continue;

      const classeNom = this.nomClasseDuCours(p.coursId);

      if (this.classeFiltreId() !== 'TOUTES' && cours.classeId !== this.classeFiltreId()) continue;
      if (this.dateDebut() && p.date < this.dateDebut()) continue;
      if (this.dateFin() && p.date > this.dateFin()) continue;

      resultat.push({
        date: p.date,
        classeNom,
        coursNom: cours.nom,
        personneNom: this.nomPersonne(p.presenceProf.personneId),
        role: 'Professeur',
        statut: LIBELLES_STATUT[p.presenceProf.statut] ?? p.presenceProf.statut,
        heureArrivee: p.presenceProf.heureArrivee ?? '-',
      });

      for (const e of p.presencesEleves) {
        resultat.push({
          date: p.date,
          classeNom,
          coursNom: cours.nom,
          personneNom: this.nomPersonne(e.personneId),
          role: 'Élève',
          statut: LIBELLES_STATUT[e.statut] ?? e.statut,
          heureArrivee: e.heureArrivee ?? '-',
        });
      }
    }

    return resultat.sort((a, b) => b.date.localeCompare(a.date));
  });

  private nomFichier(extension: string): string {
    const horodatage = new Date().toISOString().substring(0, 10);
    return `historique-appels-${horodatage}.${extension}`;
  }

  private enTetes = ['Date', 'Classe', 'Cours', 'Personne', 'Rôle', 'Statut', "Heure d'arrivée"];

  private versLignesTableau(): string[][] {
    return this.lignes().map((l) => [l.date, l.classeNom, l.coursNom, l.personneNom, l.role, l.statut, l.heureArrivee]);
  }

  exporterCsv(): void {
    const lignes = [this.enTetes, ...this.versLignesTableau()];
    const contenu = lignes.map((ligne) => ligne.map((c) => `"${c.replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + contenu], { type: 'text/csv;charset=utf-8;' });
    this.telecharger(blob, this.nomFichier('csv'));
  }

  exporterExcel(): void {
    const feuille = XLSX.utils.aoa_to_sheet([this.enTetes, ...this.versLignesTableau()]);
    const classeur = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(classeur, feuille, 'Appels');
    XLSX.writeFile(classeur, this.nomFichier('xlsx'));
  }

  exporterPdf(): void {
    const doc = new jsPDF({ orientation: 'landscape' });
    doc.setFontSize(14);
    doc.text('Historique des appels de présence', 14, 15);

    autoTable(doc, {
      head: [this.enTetes],
      body: this.versLignesTableau(),
      startY: 22,
      styles: { fontSize: 8 },
      headStyles: { fillColor: [124, 111, 219] },
    });

    doc.save(this.nomFichier('pdf'));
  }

  exporterWord(): void {
    const lignesHtml = this.versLignesTableau()
      .map((ligne) => `<tr>${ligne.map((c) => `<td>${c}</td>`).join('')}</tr>`)
      .join('');

    const html = `
      <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word">
        <head><meta charset="utf-8"><title>Historique des appels</title></head>
        <body>
          <h2>Historique des appels de présence</h2>
          <table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-family:Arial;font-size:11px;">
            <thead><tr>${this.enTetes.map((h) => `<th>${h}</th>`).join('')}</tr></thead>
            <tbody>${lignesHtml}</tbody>
          </table>
        </body>
      </html>
    `;

    const blob = new Blob(['\ufeff' + html], { type: 'application/msword' });
    this.telecharger(blob, this.nomFichier('doc'));
  }

  private telecharger(blob: Blob, nomFichier: string): void {
    const url = URL.createObjectURL(blob);
    const lien = document.createElement('a');
    lien.href = url;
    lien.download = nomFichier;
    lien.click();
    URL.revokeObjectURL(url);
  }
}