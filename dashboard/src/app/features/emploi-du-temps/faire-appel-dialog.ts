import { Component, Inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { PresenceCoursService } from '../../core/services/presence-cours';
import { PresenceCours, PresenceIndividuelle } from '../../core/models/presence';
import { Personne } from '../../core/models';

export interface DonneesFaireAppel {
  coursId: string;
  coursNom: string;
  date: string; // "YYYY-MM-DD" — date de départ, modifiable ensuite dans le dialogue
  personnes: Personne[];
}

const LIBELLES_STATUT: Record<string, string> = {
  PRESENT: 'Présent',
  RETARD: 'Retard',
  ABSENT: 'Absent',
};

@Component({
  selector: 'app-faire-appel-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>Appel — {{ data.coursNom }}</h2>

    <div class="ligne-date">
      <input type="date" [(ngModel)]="dateSelectionnee" (ngModelChange)="chargerAppel()" class="input-date" />
      @if (presence()?.statutSeance === 'VALIDEE') {
        <span class="badge-valide">
          <mat-icon>check_circle</mat-icon>
          Déjà validé
        </span>
      } @else if (presence()) {
        <span class="badge-proposition">Proposition non validée</span>
      }
    </div>

    <mat-dialog-content>
      @if (chargement()) {
        <p class="loading-state">Chargement de la proposition...</p>
      } @else if (erreurChargement()) {
        <div class="message-erreur">
          <mat-icon>error_outline</mat-icon>
          {{ erreurChargement() }}
        </div>
      } @else if (presence()) {
        <!-- ============ Professeur ============ -->
        <div class="section-titre">Professeur</div>
        <div class="ligne-personne">
          <span class="nom-personne">{{ nomPersonne(presence()!.presenceProf.personneId) }}</span>
          <div class="statut-boutons">
            @for (s of statuts; track s) {
              <button
                type="button"
                class="statut-btn"
                [class.actif]="presence()!.presenceProf.statut === s"
                [class]="'statut-' + s.toLowerCase()"
                (click)="changerStatutProf(s)"
              >
                {{ libelle(s) }}
              </button>
            }
          </div>
          @if (presence()!.presenceProf.heureArrivee) {
            <span class="heure-arrivee">{{ presence()!.presenceProf.heureArrivee }}</span>
          }
        </div>

        <!-- ============ Élèves ============ -->
        <div class="section-titre">Élèves ({{ presence()!.presencesEleves.length }})</div>
        @for (p of presence()!.presencesEleves; track p.personneId) {
          <div class="ligne-personne">
            <span class="nom-personne">{{ nomPersonne(p.personneId) }}</span>
            <div class="statut-boutons">
              @for (s of statuts; track s) {
                <button
                  type="button"
                  class="statut-btn"
                  [class.actif]="p.statut === s"
                  [class]="'statut-' + s.toLowerCase()"
                  (click)="changerStatutEleve(p.personneId, s)"
                >
                  {{ libelle(s) }}
                </button>
              }
            </div>
            @if (p.heureArrivee) {
              <span class="heure-arrivee">{{ p.heureArrivee }}</span>
            }
          </div>
        }

        @if (presence()!.statutSeance === 'PREREMPLIE') {
          <p class="note-preremplie">
            <mat-icon>auto_awesome</mat-icon>
            Proposition calculée à partir des passages enregistrés — vérifiez et corrigez si besoin avant de valider.
          </p>
        }
      }

      @if (erreurValidation()) {
        <div class="message-erreur">
          <mat-icon>error_outline</mat-icon>
          {{ erreurValidation() }}
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Annuler</button>
      <button mat-flat-button class="btn-primary" [disabled]="!presence() || validationEnCours()" (click)="valider()">
        {{ validationEnCours() ? 'Enregistrement...' : "Valider l'appel" }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      h2[mat-dialog-title] {
        font-family: 'Playfair Display', serif;
        color: var(--color-text);
        margin-bottom: 0;
      }
      .ligne-date {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin: 0 0 1rem;
      }
      .input-date {
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 0.4rem 0.6rem;
        font-family: inherit;
        font-size: 0.85rem;
        background: var(--color-bg);
        color: var(--color-text);
      }
      .badge-valide {
        display: flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.72rem;
        font-weight: 700;
        color: #0e8f6b;
        background: rgba(14, 143, 107, 0.12);
        padding: 0.2rem 0.6rem;
        border-radius: 20px;

        mat-icon {
          font-size: 14px;
          width: 14px;
          height: 14px;
        }
      }
      .badge-proposition {
        font-size: 0.72rem;
        font-weight: 700;
        color: var(--color-text-muted);
        background: var(--color-bg);
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
      }
      .loading-state {
        color: var(--color-text-muted);
      }
      .section-titre {
        font-weight: 700;
        font-size: 0.75rem;
        letter-spacing: 0.4px;
        text-transform: uppercase;
        color: var(--color-text-muted);
        margin: 1.1rem 0 0.5rem;

        &:first-of-type {
          margin-top: 0;
        }
      }
      .ligne-personne {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--color-border);
      }
      .nom-personne {
        flex: 1;
        font-size: 0.88rem;
        color: var(--color-text);
      }
      .statut-boutons {
        display: flex;
        gap: 0.3rem;
      }
      .statut-btn {
        border: 1px solid var(--color-border);
        background: transparent;
        color: var(--color-text-muted);
        font-size: 0.72rem;
        font-weight: 600;
        padding: 0.3rem 0.6rem;
        border-radius: 20px;
        cursor: pointer;
        transition: all 0.15s ease;

        &:hover {
          border-color: var(--color-accent);
        }

        &.actif.statut-present {
          background: rgba(14, 143, 107, 0.14);
          border-color: #0e8f6b;
          color: #0e8f6b;
        }
        &.actif.statut-retard {
          background: rgba(201, 130, 42, 0.14);
          border-color: #c9822a;
          color: #c9822a;
        }
        &.actif.statut-absent {
          background: rgba(214, 69, 80, 0.14);
          border-color: #d64550;
          color: #d64550;
        }
      }
      .heure-arrivee {
        font-size: 0.72rem;
        color: var(--color-text-muted);
        min-width: 42px;
        text-align: right;
      }
      .note-preremplie {
        display: flex;
        align-items: center;
        gap: 0.4rem;
        font-size: 0.78rem;
        color: var(--color-text-muted);
        background: var(--color-bg);
        padding: 0.6rem 0.8rem;
        border-radius: 8px;
        margin-top: 1rem;

        mat-icon {
          font-size: 16px;
          width: 16px;
          height: 16px;
          color: var(--color-accent);
          flex-shrink: 0;
        }
      }
      .message-erreur {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        background: #fbeaec;
        color: #d64550;
        padding: 0.75rem 1rem;
        border-radius: 10px;
        font-size: 0.85rem;
        margin-top: 0.75rem;

        mat-icon {
          font-size: 20px;
          width: 20px;
          height: 20px;
          flex-shrink: 0;
        }
      }
    `,
  ],
})
export class FaireAppelDialog {
  presence = signal<PresenceCours | null>(null);
  chargement = signal(true);
  erreurChargement = signal<string | null>(null);
  erreurValidation = signal<string | null>(null);
  validationEnCours = signal(false);
  dateSelectionnee: string;

  statuts: Array<'PRESENT' | 'RETARD' | 'ABSENT'> = ['PRESENT', 'RETARD', 'ABSENT'];

  constructor(
    private presenceCoursService: PresenceCoursService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<FaireAppelDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: DonneesFaireAppel,
  ) {
    this.dateSelectionnee = data.date;
    this.chargerAppel();
  }

  /**
   * NOUVEAU — cherche D'ABORD un appel déjà VALIDÉ pour cette date
   * précise ; ne recalcule une proposition (preremplir) que si aucun
   * appel n'a encore été validé ce jour-là. Sans ça, rouvrir l'appel
   * d'un jour précédent ignorait silencieusement ce qui avait déjà
   * été validé et corrigé par un humain.
   */
  chargerAppel(): void {
    this.chargement.set(true);
    this.erreurChargement.set(null);

    this.presenceCoursService.lister(this.data.coursId, this.dateSelectionnee).subscribe({
      next: (appelsExistants) => {
        if (appelsExistants.length > 0) {
          this.presence.set(appelsExistants[0]);
          this.chargement.set(false);
        } else {
          this.chargerPreremplissage();
        }
      },
      error: () => this.chargerPreremplissage(), // repli : on tente quand même la proposition
    });
  }

  private chargerPreremplissage(): void {
    this.presenceCoursService.preremplir(this.data.coursId, this.dateSelectionnee).subscribe({
      next: (p) => {
        this.presence.set(p);
        this.chargement.set(false);
      },
      error: (err) => {
        this.erreurChargement.set(
          err?.error?.message ?? "Impossible de charger la proposition d'appel.",
        );
        this.chargement.set(false);
      },
    });
  }

  nomPersonne(id: string): string {
    const p = this.data.personnes.find((x) => x.id === id);
    return p ? `${p.nom} ${p.prenom ?? ''}`.trim() : 'Inconnu';
  }

  libelle(statut: string): string {
    return LIBELLES_STATUT[statut] ?? statut;
  }

  changerStatutProf(statut: 'PRESENT' | 'RETARD' | 'ABSENT'): void {
    const p = this.presence();
    if (!p) return;
    this.presence.set({ ...p, presenceProf: { ...p.presenceProf, statut } });
  }

  changerStatutEleve(personneId: string, statut: 'PRESENT' | 'RETARD' | 'ABSENT'): void {
    const p = this.presence();
    if (!p) return;
    const presencesEleves = p.presencesEleves.map((e) =>
      e.personneId === personneId ? { ...e, statut } : e,
    );
    this.presence.set({ ...p, presencesEleves });
  }

  valider(): void {
    const p = this.presence();
    if (!p) return;

    this.erreurValidation.set(null);
    this.validationEnCours.set(true);

    this.presenceCoursService.valider(p).subscribe({
      next: () => {
        this.validationEnCours.set(false);
        this.dialogRef.close(true);
      },
      error: (err) => {
        this.validationEnCours.set(false);
        const message = err?.error?.message ?? "Une erreur est survenue, l'appel n'a pas pu être enregistré.";
        this.erreurValidation.set(message);
        this.snackBar.open(message, 'Fermer', { duration: 6000 });
      },
    });
  }
}