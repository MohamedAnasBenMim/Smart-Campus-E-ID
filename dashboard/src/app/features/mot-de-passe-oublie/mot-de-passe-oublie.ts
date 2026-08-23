import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { Auth } from '../../core/auth';

@Component({
  selector: 'app-mot-de-passe-oublie',
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
  templateUrl: './mot-de-passe-oublie.html',
  styleUrl: './mot-de-passe-oublie.scss',
})
export class MotDePasseOubliePage {
  form: FormGroup;
  envoiEnCours = signal(false);
  messageConfirmation = signal<string | null>(null);
  erreur = signal<string | null>(null);

  constructor(
    private fb: FormBuilder,
    private auth: Auth,
  ) {
    this.form = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
    });
  }

  soumettre(): void {
    if (this.form.invalid) return;

    this.envoiEnCours.set(true);
    this.erreur.set(null);
    this.messageConfirmation.set(null);

    this.auth.motDePasseOublie(this.form.value.email).subscribe({
      next: (reponse) => {
        this.envoiEnCours.set(false);
        this.messageConfirmation.set(reponse.message);
      },
      error: () => {
        this.envoiEnCours.set(false);
        // Message générique volontaire, même en cas d'erreur technique —
        // cohérent avec le comportement "toujours pareil" côté backend.
        this.messageConfirmation.set(
          "Si un compte existe avec cet email, un lien de réinitialisation vient d'être envoyé.",
        );
      },
    });
  }
}