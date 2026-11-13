
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';

import { CoachesField, CoachesService, Coach } from '../coaches.service';
import { Club } from '../../clubs/clubs.service';
import { COACHES_FIELD_LABELS, HIDDEN_FIELDS } from '../coaches-fields.maps'

@Component({
  imports: [CommonModule, FormsModule],
  selector: 'app-coaches-list',
  standalone: true,
  templateUrl: './coaches-list.html',
  styleUrl: './coaches-list.scss'
})
export class CoachesList implements OnInit {
  private route = inject(ActivatedRoute);
  private service = inject(CoachesService);

  tournamentId = 0;

  coaches = signal<Coach[]>([]);
  clubs = signal<Club[]>([]);
  fields = signal<CoachesField[]>([]);

  labelFields = COACHES_FIELD_LABELS;
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
      this.error.set('Не удалось определить тренера');
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
          next: coaches => {
            this.coaches.set(coaches);
            this.loading.set(false);
            this.loadClubs();
          },
          error: () => {
            this.error.set('Не удалось загрузить тренеров');
            this.loading.set(false);
          }
        });
      },
      error: () => {
        this.error.set('Не удалось получить структуру таблицы тренеров');
        this.loading.set(false);
      }
    });
  }

  loadClubs(): void {
    this.service.getClubs(this.tournamentId).subscribe({
      next: (data) => {
        this.clubs.set(data);
      },
      error: () => {
        this.error.set('Не удалось загрузить клубы');
      }
    })
  }

  getClubName(clubId: number | null | undefined): unknown {
    if (clubId == null) {
      return '—';
    }

    return this.clubs().find(club => club.id === clubId)?.['name'] ?? '—';
  }

  openCreate(): void {
    this.editingId.set(null);
    this.formData = {};
    this.formOpen.set(true);
  }

  openEdit(coach: Coach): void {
    this.editingId.set(coach.id);
    this.formData = { ...coach };
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
        this.error.set(err.error?.detail || 'Ошибка сохранения тренера');
        this.saving.set(false);
      }
    });
  }

  remove(coach: Coach): void {
    const name = `${coach['last_name']} ${(coach['first_name'] as string)?.[0] ?? ''}.${(coach['second_name'] as string)?.[0] ?? ''}.`

    if (!confirm(`Удалить тренера "${name}"?`)) {
      return;
    }

    this.service.delete(this.tournamentId, coach['id']).subscribe({
      next: () => this.load(),
      error: () => this.error.set('Не удалось удалить тренера')
    });
  }

  isDateField(field: CoachesField): boolean {
    return field.type.toLowerCase().includes('date');
  }
  
}