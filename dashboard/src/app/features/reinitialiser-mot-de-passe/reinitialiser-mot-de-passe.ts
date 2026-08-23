import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Auth } from '../../core/auth';

function motsDePasseIdentiquesValidator(control: AbstractControl): ValidationErrors | null {
  const motDePasse = control.get('nouveauMotDePasse')?.value;
  const confirmation = control.get('confirmation')?.value;
  return motDePasse === confirmation ? null : { motsDePasseDifferents: true };
}

@Component({
  selector: 'app-reinitialiser-mot-de-passe',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatIconModule,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
  ],
  templateUrl: './reinitialiser-mot-de-passe.html',
  styleUrl: './reinitialiser-mot-de-passe.scss',
})
export class ReinitialiserMotDePassePage implements OnInit {
  form: FormGroup;
  token: string | null = null;
  tokenAbsent = signal(false);
  envoiEnCours = signal(false);
  succes = signal(false);
  erreur = signal<string | null>(null);

  constructor(
    private fb: FormBuilder,
    private auth: Auth,
    private route: ActivatedRoute,
    private router: Router,
  ) {
    this.form = this.fb.group(
      {
        nouveauMotDePasse: ['', [Validators.required, Validators.minLength(8)]],
        confirmation: ['', Validators.required],
      },
      { validators: motsDePasseIdentiquesValidator },
    );
  }

  ngOnInit(): void {
    this.token = this.route.snapshot.queryParamMap.get('token');
    if (!this.token) {
      this.tokenAbsent.set(true);
    }
  }

  soumettre(): void {
    if (this.form.invalid || !this.token) return;

    this.envoiEnCours.set(true);
    this.erreur.set(null);

    this.auth.reinitialiserMotDePasse(this.token, this.form.value.nouveauMotDePasse).subscribe({
      next: () => {
        this.envoiEnCours.set(false);
        this.succes.set(true);
        setTimeout(() => this.router.navigate(['/login']), 3000);
      },
      error: (err) => {
        this.envoiEnCours.set(false);
        this.erreur.set(err?.error?.message ?? 'Une erreur est survenue.');
      },
    });
  }
}