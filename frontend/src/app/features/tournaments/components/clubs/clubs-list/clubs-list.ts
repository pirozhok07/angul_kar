
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';

import { ClubsService, Club, ClubsField } from '../clubs.service';
import { CLUBS_FIELD_LABELS, HIDDEN_FIELDS } from '../clubs-fields.maps'

@Component({
  imports: [CommonModule, FormsModule],
  selector: 'app-clubs-list',
  standalone: true,
  templateUrl: './clubs-list.html',
  styleUrl: './clubs-list.scss'
})
export class ClubsList implements OnInit {
  private route = inject(ActivatedRoute);
  private service = inject(ClubsService);

  tournamentId = 0;

  clubs = signal<Club[]>([]);
  fields = signal<ClubsField[]>([]);

  labelFields = CLUBS_FIELD_LABELS;
  visibleFields = computed(() => {
    return this.fields().filter(field => ! HIDDEN_FIELDS.includes(field.name))
  });

  loading = signal(false);
  error = signal('');
  formOpen = signal(false);
  editingId = signal<number | null>(null);

  previewData = signal<any>(null);
  previewOpen = signal(false);
  saving = signal(false);

  formData: Record<string, unknown> = {};

  ngOnInit(): void {
    const id = Number(
      this.route.parent?.snapshot.paramMap.get('id')
    );

    if (!Number.isInteger(id) || id <= 0) {
      this.error.set('Не удалось определить турнир');
      return;
    }

    this.tournamentId = id;
    this.load();
  }

  load(): void {
    this.loading.set(true);
    
    this.service.getFields(this.tournamentId).subscribe({
      next: fields => {
        this.fields.set(fields);
        this.service.getAll(this.tournamentId).subscribe({
          next: clubs => {
            this.clubs.set(clubs);
            this.loading.set(false);
          },
          error: () => {
            this.error.set('Не удалось загрузить клубы');
            this.loading.set(false);
          }
        });
      },
      error: () => {
        this.error.set('Не удалось получить структуру таблицы клубов');
        this.loading.set(false);
      }
    });
  }

  openCreate(): void {
    this.editingId.set(null);
    this.formData = {};
    this.formOpen.set(true);
  }

  openEdit(club: Club): void {
    this.editingId.set(club.id);
    this.formData = { ...club };
    this.formOpen.set(true);
  }

  save(): void {
    this.saving.set(true);

    const data = { ...this.formData };
    delete data['id'];

    const request = this.editingId()
      ? this.service.update(
          this.tournamentId,
          this.editingId()!,
          data
        )
      : this.service.create(this.tournamentId, data);

    request.subscribe({
      next: () => {
        this.formOpen.set(false);
        this.saving.set(false);
        this.load();
      },
      error: err => {
        this.error.set(err.error?.detail || 'Ошибка сохранения клуба');
        this.saving.set(false);
      }
    });
  }

  remove(club: Club): void {
    if (!confirm(`Удалить категорию "${club['name']}"?`)) {
      return;
    }

    this.service.delete(this.tournamentId, club['id']).subscribe({
      next: () => this.load(),
      error: () => this.error.set('Не удалось удалить клуб')
    });
  }

  isDateField(field: ClubsField): boolean {
    return field.type.toLowerCase().includes('date');
  }
  
}