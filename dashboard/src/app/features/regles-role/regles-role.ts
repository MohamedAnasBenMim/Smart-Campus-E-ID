import { Component, OnInit, signal, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ReglesRoleService } from '../../core/services/regles-role';
import { Zones as ZonesService } from '../../core/services/zones';
import { RegleAccesRole } from '../../core/models/regle-role';
import { Zone } from '../../core/models';
import { ConfirmDialog } from '../../shared/components/confirm-dialog/confirm-dialog';

const ROLES = [
  { valeur: 'SURVEILLANT', libelle: 'Surveillant' },
  { valeur: 'DIRECTEUR', libelle: 'Directeur' },
  { valeur: 'AGENT_DE_DIRECTION', libelle: 'Agent de direction' },
  { valeur: 'PROF', libelle: 'Professeur' },
  { valeur: 'ELEVE', libelle: 'Élève' },
  { valeur: 'PERSONNEL', libelle: 'Personnel' },
];

interface DonneesDialogueRegleRole {
  zones: Zone[];
  regleExistante?: RegleAccesRole; // présente = mode modification
}

// ============================================================
// Dialogue de création ET modification
// ============================================================
@Component({
  selector: 'app-creer-regle-role-dialog',
  standalone: true,
  imports: [ReactiveFormsModule, MatDialogModule, MatButtonModule, MatFormFieldModule, MatSelectModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>{{ modeModification ? "Modifier la règle par rôle" : "Nouvelle règle par rôle" }}</h2>

    <mat-dialog-content>
      <form [formGroup]="form" class="regle-form">
        <mat-form-field appearance="outline" class="full-width">
          <mat-label>Rôle</mat-label>
          <mat-select formControlName="role">
            @for (r of roles; track r.valeur) {
              <mat-option [value]="r.valeur">{{ r.libelle }}</mat-option>
            }
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline" class="full-width">
          <mat-label>{{ modeModification ? 'Zone' : 'Zones (sélection multiple)' }}</mat-label>
          @if (modeModification) {
            <mat-select formControlName="zoneId">
              @for (z of data.zones; track z.id) {
                <mat-option [value]="z.id">{{ z.nom }}</mat-option>
              }
            </mat-select>
          } @else {
            <mat-select formControlName="zoneIds" multiple>
              @for (z of data.zones; track z.id) {
                <mat-option [value]="z.id">{{ z.nom }}</mat-option>
              }
            </mat-select>
          }
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

      <p class="note-explicative">
        <mat-icon>info_outline</mat-icon>
        Toute personne ayant ce rôle aura accès à cette zone, sur ce créneau — utile pour le personnel
        (surveillants, direction...). Élèves et profs sont normalement déjà couverts automatiquement par
        leurs cours, sans avoir besoin de règle ici.
      </p>

      @if (erreur()) {
        <div class="message-erreur">
          <mat-icon>error_outline</mat-icon>
          {{ erreur() }}
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="dialogRef.close()">Annuler</button>
      <button mat-flat-button class="btn-primary" [disabled]="form.invalid" (click)="soumettre()">
        {{ modeModification ? 'Enregistrer les modifications' : 'Créer la règle' }}
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
      .note-explicative {
        display: flex;
        align-items: flex-start;
        gap: 0.5rem;
        background: var(--color-bg);
        color: var(--color-text-muted);
        padding: 0.7rem 0.9rem;
        border-radius: 10px;
        font-size: 0.78rem;
        line-height: 1.4;
        margin-top: 1rem;

        mat-icon {
          font-size: 18px;
          width: 18px;
          height: 18px;
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
export class CreerRegleRoleDialog {
  form: FormGroup;
  modeModification: boolean;
  erreur = signal<string | null>(null);
  roles = ROLES;

  constructor(
    private fb: FormBuilder,
    private reglesRoleService: ReglesRoleService,
    private snackBar: MatSnackBar,
    public dialogRef: MatDialogRef<CreerRegleRoleDialog, boolean>,
    @Inject(MAT_DIALOG_DATA) public data: DonneesDialogueRegleRole,
  ) {
    this.modeModification = !!data?.regleExistante;
    const r = data?.regleExistante;

    this.form = this.fb.group({
      role: [r?.role ?? 'SURVEILLANT', Validators.required],
      zoneId: [r?.zoneId ?? ''], // utilisé seulement en modification
      zoneIds: [[]], // utilisé seulement en création (multi-sélection)
      horaireDebut: [r?.horaireDebut?.substring(0, 5) ?? '08:00', Validators.required],
      horaireFin: [r?.horaireFin?.substring(0, 5) ?? '18:00', Validators.required],
    });

    // Validateur conditionnel : au moins une zone requise, selon le mode
    if (this.modeModification) {
      this.form.get('zoneId')?.setValidators(Validators.required);
    } else {
      this.form.get('zoneIds')?.setValidators(Validators.required);
    }
    this.form.get('zoneId')?.updateValueAndValidity();
    this.form.get('zoneIds')?.updateValueAndValidity();
  }

 soumettre(): void {
  if (this.form.invalid) return;
  this.erreur.set(null);

  const { role, zoneId, zoneIds, horaireDebut, horaireFin } = this.form.value;

  const gererErreur = (err: any) => {
    const message = err?.error?.message ?? 'Une erreur est survenue.';
    this.erreur.set(message);
    this.snackBar.open(message, 'Fermer', { duration: 6000 });
  };

  if (this.modeModification) {
    this.reglesRoleService.modifier(this.data.regleExistante!.id, { role, zoneId, horaireDebut, horaireFin }).subscribe({
      next: () => this.dialogRef.close(true),
      error: gererErreur,
    });
  } else {
    this.reglesRoleService.creerEnLot({ role, zoneIds, horaireDebut, horaireFin }).subscribe({
      next: () => this.dialogRef.close(true),
      error: gererErreur,
    });
  }
}
}

// ============================================================
// Page principale
// ============================================================
@Component({
  selector: 'app-regles-role',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule],
  templateUrl: './regles-role.html',
  styleUrl: './regles-role.scss',
})
export class ReglesRolePage implements OnInit {
  regles = signal<RegleAccesRole[]>([]);
  zones = signal<Zone[]>([]);
  chargement = signal(true);

  constructor(
    private reglesRoleService: ReglesRoleService,
    private zonesService: ZonesService,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.zonesService.lister().subscribe((z) => this.zones.set(z));
    this.reglesRoleService.lister().subscribe({
      next: (regles) => {
        this.regles.set(regles);
        this.chargement.set(false);
      },
      error: () => this.chargement.set(false),
    });
  }

  libelleRole(role: string): string {
    return ROLES.find((r) => r.valeur === role)?.libelle ?? role;
  }

  nomZone(id: string): string {
    return this.zones().find((z) => z.id === id)?.nom ?? 'Zone inconnue';
  }

  ouvrirCreation(): void {
    const ref = this.dialog.open(CreerRegleRoleDialog, {
      width: '480px',
      panelClass: 'app-dialog',
      data: { zones: this.zones() },
    });

    ref.afterClosed().subscribe((succes) => {
      if (succes) this.charger();
    });
  }

  ouvrirModification(regle: RegleAccesRole): void {
    const ref = this.dialog.open(CreerRegleRoleDialog, {
      width: '480px',
      panelClass: 'app-dialog',
      data: { zones: this.zones(), regleExistante: regle },
    });

    ref.afterClosed().subscribe((succes) => {
      if (succes) {
        this.snackBar.open('Règle modifiée.', 'Fermer', { duration: 3000 });
        this.charger();
      }
    });
  }

  supprimer(regle: RegleAccesRole): void {
    const ref = this.dialog.open(ConfirmDialog, {
      width: '400px',
      panelClass: 'app-dialog',
      data: {
        titre: 'Supprimer cette règle ?',
        message: `Le rôle "${this.libelleRole(regle.role)}" perdra l'accès autorisé à "${this.nomZone(regle.zoneId)}".`,
        labelConfirmer: 'Supprimer',
        dangereux: true,
      },
    });

    ref.afterClosed().subscribe((confirme) => {
      if (!confirme) return;
      this.reglesRoleService.supprimer(regle.id).subscribe(() => {
        this.snackBar.open('Règle supprimée.', 'Fermer', { duration: 3000 });
        this.charger();
      });
    });
  }
}