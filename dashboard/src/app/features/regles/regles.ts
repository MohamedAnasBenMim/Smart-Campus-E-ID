import { Component, OnInit, signal, computed, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Regles as ReglesService } from '../../core/services/regles';
import { Zones as ZonesService } from '../../core/services/zones';
import { Personnes as PersonnesService } from '../../core/services/personnes';
import { RegleAcces, Personne, Zone } from '../../core/models';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';

interface DonneesDialogueRegle {
  personnes: Personne[];
  zones: Zone[];
}

// ============================================================
// Dialogue de création
// ============================================================
@Component({
  selector: 'app-creer-regle-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>Nouvelle règle d'accès</h2>

    <mat-dialog-content>
      <form [formGroup]="form" class="regle-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Personne</mat-label>
          <mat-select formControlName="personneId">
            @for (p of data.personnes; track p.id) {
              <mat-option [value]="p.id">{{ p.nom }} {{ p.prenom }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Zone</mat-label>
          <mat-select formControlName="zoneId">
            @for (z of data.zones; track z.id) {
              <mat-option [value]="z.id">{{ z.nom }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <div class="horaires-row">
          <label class="time-field">
            <span>Horaire début</span>
            <input type="time" formControlName="horaireDebut" />
          </label>
          <label class="time-field">
            <span>Horaire fin</span>
            <input type="time" formControlName="horaireFin" />
          </label>
        </div>
      </form>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Annuler</button>
      <button mat-flat-button class="btn-primary" [disabled]="form.invalid" (click)="soumettre()">
        Créer la règle
      </button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      h2[mat-dialog-title] {
        font-family: 'Playfair Display', serif;
        color: var(--color-text);
      }
      .regle-form {
        display: flex;
        flex-direction: column;
        min-width: 380px;
      }
      .full-width {
        width: 100%;
      }
      .horaires-row {
        display: flex;
        gap: 1rem;
        margin-top: 0.5rem;
      }
      .time-field {
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 0.4rem;
        font-size: 0.8rem;
        color: var(--color-text-muted);
      }
      .time-field input {
        border: 1px solid var(--color-border);
        border-radius: 8px;
        padding: 0.6rem 0.7rem;
        font-family: inherit;
        font-size: 0.95rem;
        background: var(--color-bg);
        color: var(--color-text);
      }
    `,
  ],
})
export class CreerRegleDialog {
  form: FormGroup;

  constructor(
    private fb: FormBuilder,
    private reglesService: ReglesService,
    public dialogRef: MatDialogRef<CreerRegleDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: DonneesDialogueRegle,
  ) {
    this.form = this.fb.group({
      personneId: ['', Validators.required],
      zoneId: ['', Validators.required],
      horaireDebut: ['08:00', Validators.required],
      horaireFin: ['18:00', Validators.required],
    });
  }

  soumettre(): void {
    if (this.form.invalid) return;
    this.reglesService.creer(this.form.value).subscribe(() => this.dialogRef.close(true));
  }
}

// ============================================================
// Page principale
// ============================================================
@Component({
  selector: 'app-regles',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './regles.html',
  styleUrl: './regles.scss',
})
export class ReglesPage implements OnInit {
  regles = signal<RegleAcces[]>([]);
  personnes = signal<Personne[]>([]);
  zones = signal<Zone[]>([]);
  chargement = signal(true);

  peutCreer = computed(() => this.personnes().length > 0 && this.zones().length > 0);

  constructor(
    private reglesService: ReglesService,
    private personnesService: PersonnesService,
    private zonesService: ZonesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.personnesService.lister().subscribe((p) => this.personnes.set(p));
    this.zonesService.lister().subscribe((z) => this.zones.set(z));
    this.reglesService.lister().subscribe({
      next: (regles) => {
        this.regles.set(regles);
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  nomPersonne(id: string): string {
    const p = this.personnes().find((x) => x.id === id);
    return p ? `${p.nom} ${p.prenom ?? ''}`.trim() : 'Personne inconnue';
  }

  nomZone(id: string): string {
    return this.zones().find((z) => z.id === id)?.nom ?? 'Zone inconnue';
  }

  ouvrirCreation(): void {
    const ref = this.dialog.open(CreerRegleDialog, {
      width: '480px',
      panelClass: 'app-dialog',
      data: { personnes: this.personnes(), zones: this.zones() },
    });

    ref.afterClosed().subscribe((succes) => {
      if (succes) this.charger();
    });
  }

  supprimer(regle: RegleAcces): void {
    const ref = this.dialog.open(ConfirmDialog, {
      width: '400px',
      panelClass: 'app-dialog',
      data: {
        titre: 'Supprimer cette règle ?',
        message: `${this.nomPersonne(regle.personneId)} perdra l'accès autorisé à "${this.nomZone(regle.zoneId)}".`,
        labelConfirmer: 'Supprimer',
        dangereux: true,
      },
    });

    ref.afterClosed().subscribe((confirme) => {
      if (!confirme) return;
      this.reglesService.supprimer(regle.id).subscribe(() => {
        this.snackBar.open('Règle supprimée.', 'Fermer', { duration: 3000 });
        this.charger();
      });
    });
  }
}