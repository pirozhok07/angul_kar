import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink, Router } from '@angular/router';
import {
  Category,
  CategoryField,
  CategoriesService
} from '../categories.service';

import { CATEGORIES_FIELD_LABELS, HIDDEN_FIELDS } from '../categories-fields.maps'

@Component({
  selector: 'app-categories-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './categories-list.html',
  styleUrl: './categories-list.scss'
})
export class CategoriesList implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly service = inject(CategoriesService);

  tournamentId = 0;

  categories = signal<Category[]>([]);
  fields = signal<CategoryField[]>([]);
  labelFields = CATEGORIES_FIELD_LABELS;
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

  form: Partial<Category> = this.emptyForm();

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

  emptyForm(): Partial<Category> {
    return {
      name: '',
      discipline: 'kata',
      age_min: 6,
      age_max: 7,
      gender: null,
      weight_min: null,
      weight_max: null
    };
  }

  load(): void {
    this.loading.set(true);

    this.service.getFields(this.tournamentId).subscribe({
      next: fields => {
        this.fields.set(fields);
        this.service.getAll(this.tournamentId).subscribe({
          next: categories => {
            this.categories.set(categories);
            this.loading.set(false);
          },
          error: () => {
            this.error.set('Не удалось загрузить категории');
            this.loading.set(false);
          }
        });
      },
      error: () => {
        this.error.set('Не удалось получить структуру таблицы категорий');
        this.loading.set(false);
      }
    });
  }

  openCreate(): void {
    this.editingId.set(null);
    this.form = this.emptyForm();
    this.formOpen.set(true);
  }

  openEdit(category: Category): void {
    this.editingId.set(category.id);
    this.form = { ...category };
    this.formOpen.set(true);
  }

  save(): void {
    this.saving.set(true);

    const request = this.editingId()
      ? this.service.update(
          this.tournamentId,
          this.editingId()!,
          this.form
        )
      : this.service.create(this.tournamentId, this.form);

    request.subscribe({
      next: () => {
        this.formOpen.set(false);
        this.saving.set(false);
        this.load();
      },
      error: err => {
        this.error.set(err.error?.detail || 'Ошибка сохранения категории');
        this.saving.set(false);
      }
    });
  }

  remove(category: Category): void {
    if (!confirm(`Удалить категорию "${category['name']}"?`)) {
      return;
    }

    this.service.delete(this.tournamentId, category['id']).subscribe({
      next: () => this.load(),
      error: () => this.error.set('Не удалось удалить категорию')
    });
  }

  showPreview(): void {
    this.service.preview(this.tournamentId).subscribe({
      next: data => {
        this.previewData.set(data);
        this.previewOpen.set(true);
      },
      error: err => {
        this.error.set(
          err.error?.detail || 'Не удалось рассчитать распределение'
        );
      }
    });
  }

  confirmDistribution(): void {
    const athletes = this.previewData()?.athletes ?? [];

    const assignments = athletes.flatMap((athlete: any) =>
      athlete.suggestions.map((suggestion: any) => ({
        athlete_id: athlete.athlete_id,
        category_id: suggestion.category_id
      }))
    );

    if (!assignments.length) {
      this.error.set('Нет подходящих назначений');
      return;
    }

    if (!confirm(`Подтвердить назначение ${assignments.length} участий?`)) {
      return;
    }

    this.service.assign(this.tournamentId, assignments).subscribe({
      next: result => {
        this.previewOpen.set(false);
        alert(`Создано назначений: ${result.created}`);
      },
      error: err => {
        this.error.set(
          err.error?.detail || 'Не удалось сохранить распределение'
        );
      }
    });
  }

  openCategory(categoryId: number): void {
    this.router.navigate([categoryId], { relativeTo: this.route});
  }
}