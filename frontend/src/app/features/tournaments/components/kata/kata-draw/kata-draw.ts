import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule, TrailingSlashPathLocationStrategy } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { KataService } from '../kata.service';
import { tick } from '@angular/core/testing';
import { INITIAL_CONFIG } from '@angular/platform-server';
import { isTypedArray } from 'util/types';

@Component({
  imports: [CommonModule, RouterLink],
  selector: 'app-kata-draw',
  standalone: true,
  styleUrl: './kata-draw.scss',
  templateUrl: './kata-draw.html',
})
export class KataDraw implements OnInit {
  private route = inject(ActivatedRoute);
  private service = inject(KataService);

  tournamentId = 0;
  categoryId = 0;

  draggedIndex = signal<number | null>(null);
  category = signal<any>(null);
  participants = signal<any[]>([]);

  loading = signal(false);
  generating = signal(false);
  saving = signal(false);

  error = signal('');
  success = signal('');

  ngOnInit(): void {
    this.tournamentId = Number(
      this.route.parent?.snapshot.paramMap.get('id')
    );

    this.categoryId = Number(
      this.route.snapshot.paramMap.get('categoryId')
    );

    if (!this.tournamentId || !this.categoryId) {
      this.error.set('Не удалось определить турнир или категорию');
      return;
    }

    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.getAll(
      this.tournamentId,
      this.categoryId
    ).subscribe({
      next: result => {
        this.category.set(result.category);
        this.participants.set(result.participants ?? []);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(
          err.error?.detail || 'Не удалось загрузить жеребьёвку'
        );
        this.loading.set(false);
      }
    });
  }

  generate(): void {
    if (!confirm('Сформировать новый порядок жеребьёвки?')) {
      return;
    }

    this.generating.set(true);
    this.error.set('');
    this.success.set('');

    this.service.generate(
      this.tournamentId,
      this.categoryId
    ).subscribe({
      next: () => {
        this.generating.set(false);
        this.success.set('Новый порядок жеребьёвки сформирован');
        this.load();
      },
      error: err => {
        this.generating.set(false);
        this.error.set(
          err.error?.detail || 'Не удалось сформировать жеребьёвку'
        );
      }
    });
  }

  onDragStart(index:number, event: DragEvent):void {
    this.draggedIndex.set(index);

    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData('text/plain', String(index));
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();

    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
    }
  }

  onDrop(targetIndex: number, event: DragEvent): void {
    event.preventDefault();
  
    const sourceIndex = this.draggedIndex();
  
    if (sourceIndex === null || sourceIndex === targetIndex) {
      this.draggedIndex.set(null);
      return;
    }
  
    const items = [...this.participants()];
    const [movedItem] = items.splice(sourceIndex, 1);
  
    items.splice(targetIndex, 0, movedItem);
  
    this.participants.set(items);
    this.draggedIndex.set(null);
  }

  onDragEnd(): void {
    this.draggedIndex.set(null);
  }

  save(): void {
    const items = this.participants().map((participant, index) => ({
      athlete_id: participant.athlete_id,
      kata_group_id: participant.kata_group_id,
      position: index + 1
    }));

    this.saving.set(true);
    this.error.set('');
    this.success.set('');

    this.service.save(
      this.tournamentId,
      this.categoryId,
      items
    ).subscribe({
      next: () => {
        this.saving.set(false);
        this.success.set('Порядок жеребьёвки сохранён');
        this.load();
      },
      error: err => {
        this.saving.set(false);
        this.error.set(
          err.error?.detail || 'Не удалось сохранить порядок'
        );
      }
    });
  }
}
