import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import {
  KataGroup, KataGroupField, KataGroupsService, KataGroupPayload
} from '../kata-groups.service';
import { Athlete } from '../../athletes/athletes.service';
import { Category } from '../../categories/categories.service';
import { KATA_GROUPS_FIELD_LABELS, HIDDEN_FIELDS } from '../kata-groups-fields.maps'
import { Club } from '../../clubs/clubs.service';

@Component({
  imports: [FormsModule],
  selector: 'app-kata-groups-list',
  standalone: true,
  styleUrl: './kata-groups-list.scss',
  templateUrl: './kata-groups-list.html',
})
export class KataGroupsList implements OnInit {
  private route = inject(ActivatedRoute);
  private service = inject(KataGroupsService);

  tournamentId = 0;

  groups = signal<KataGroup[]>([]);
  athletes = signal<Athlete[]>([]);
  categories = signal<Category[]>([]);
  fields = signal<KataGroupField[]>([]);
  labelFields = KATA_GROUPS_FIELD_LABELS;

  visibleFields = computed(() => {
    return this.fields().filter(field => ! HIDDEN_FIELDS.includes(field.name))
  });

  formFields = computed(() =>
    this.fields().filter(field =>
      !['id', 'athletes', 'category_id'].includes(field.name)
    )
  );

  loading = signal(false);
  saving = signal(false);
  error = signal('');

  formOpen = signal(false);
  editingId = signal<number | null>(null);

  selectedAthleteIds = signal<number[]>([]);
  selectedCategoryName= signal('');

  formData: Record<string, unknown> = {};
  
  clubs = signal<Club[]>([]);
  searchLastName = signal('');
  filterAge = signal('');
  filterGender = signal('');
  filterClub = signal<number | null>(null);

  filteredAthletes = computed(() => {
    const search = this.searchLastName().trim().toLowerCase();
    const age = this.filterAge();
    const gender = this.filterGender();
    const clubId = this.filterClub();
    const selectedIds = this.selectedAthleteIds();
    
    return [...this.athletes()]
      .filter(athlete => {
        const lastName = String(
          athlete['last_name'] ?? ''
        ).toLowerCase();
  
        if (search && !lastName.includes(search)) {
          return false;
        }
  
        const athleteAge = Number(athlete['age']);
  
        if (age === '8-9' && (athleteAge < 8 || athleteAge > 9)) return false;
        if (age === '10-11' && (athleteAge < 10 || athleteAge > 11)) return false;
        if (age === '12-13' && (athleteAge < 12 || athleteAge > 13)) return false;
        if (age === '14-15' && (athleteAge < 14 || athleteAge > 15)) return false;
        if (age === '16-17' && (athleteAge < 16 || athleteAge > 17)) return false;
        if (age === '18+' && athleteAge < 18) return false;
  
        if (
          gender &&
          String(athlete['gender'] ?? '') !== gender
        ) {
          return false;
        }
  
        if (
          clubId !== null &&
          Number(athlete['club_id']) !== clubId
        ) {
          return false;
        }
  
        return true;
      })
      .sort((a, b) => {
        const aSelected = selectedIds.includes(a.id);
        const bSelected = selectedIds.includes(b.id);
  
        return Number(bSelected) - Number(aSelected);
      });
  });

  ngOnInit(): void {
    const id = Number(
      this.route.parent?.snapshot.paramMap.get('id')
    );

    if (!Number.isInteger(id) || id <= 0) {
      this.error.set('Не удалось определить ID турнира');
      return;
    }

    this.tournamentId = id;
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.error.set('');

    this.service.getFields(this.tournamentId).subscribe({
      next: fields => {
        this.fields.set(fields);

        this.service.getAll(this.tournamentId).subscribe({
          next: groups => {
            this.groups.set(groups);
            this.loading.set(false);
            this.loadCategories();
            this.loadAthletes();
            this.loadClubs();
          },
          error: err => {
            console.error(err);
            this.error.set('Не удалось загрузить ката-группы');
            this.loading.set(false);
          }
        });
      },
      error: err => {
        console.error(err);
        this.error.set('Не удалось получить структуру таблицы ката-групп');
        this.loading.set(false);
      }
    });
  }

  loadCategories(): void {
    this.service.getCategories(this.tournamentId).subscribe({
      next: data => this.categories.set(data),
      error: err => {
        console.error(err);
        this.error.set('Не удалось загрузить категории');
      }
    });
  }

  loadAthletes(): void {
    this.service.getAthletes(this.tournamentId).subscribe({
      next: data => this.athletes.set(data),
      error: err => {
        console.error(err);
        this.error.set('Не удалось загрузить спортсменов');
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

  onClubChange(event: any): void {
    const value = event === null  || event === '' ? null : Number(event);
    this.filterClub.set(value);
  }

  openCreate(): void {
    this.editingId.set(null);
    this.formData = {};
    this.selectedAthleteIds.set([]);
    this.selectedCategoryName.set('');
    this.error.set('');
    this.formOpen.set(true);
  }

  openEdit(group: KataGroup): void {
    this.editingId.set(group.id);
    this.formData = { ...group };

    const groupAthletes = group['athletes'] as Athlete[] | undefined;

    this.selectedAthleteIds.set(
      groupAthletes?.map(athlete => athlete.id) ?? []
    );

    this.updateGroupDetails(); 

    this.error.set('');
    this.formOpen.set(true);
  }

  closeForm(): void {
    this.formOpen.set(false);
    this.editingId.set(null);
    this.formData = {};
    this.selectedAthleteIds.set([]);
  }

  toggleAthlete(athleteId: number, checked: boolean): void {
    const selected = this.selectedAthleteIds();
  
    if (checked) {
      if (selected.length >= 3) {
        this.error.set('В группе должно быть ровно 3 спортсмена.');
        return;
      }
  
      if (!selected.includes(athleteId)) {
        this.selectedAthleteIds.set([...selected, athleteId]);
      }
    } else {
      this.selectedAthleteIds.set(
        selected.filter(id => id !== athleteId)
      );
    }
  
    this.updateGroupDetails();
  }

  getAthleteName(athlete: Athlete): string {
    const lastName = String(athlete['last_name'] ?? '');
    const firstName = String(athlete['first_name'] ?? '');
    const secondName = String(athlete['second_name'] ?? '');

    return `${lastName} ${firstName} ${secondName}`.trim();
  }

  getAgeGroup(age: number): string | null {
    if (age >= 8 && age <= 9) return '8-9';
    if (age >= 10 && age <= 11) return '10-11';
    if (age >= 12 && age <= 13) return '12-13';
    if (age >= 14 && age <= 15) return '14-15';
    if (age >= 16 && age <= 17) return '16-17';
    if (age >= 18) return '18+';
  
    return null;
  }
  
  getCategoryName(ageGroup: any): string {
    return `Ката-группа ${ageGroup}`;
  }

  updateGroupDetails(): void {
    const selected = this.athletes().filter(athlete =>
      this.selectedAthleteIds().includes(athlete.id)
    );
  
    // Название формируется из фамилий выбранных спортсменов.
    this.formData['name'] = selected
      .map(athlete => String(athlete['last_name'] ?? '').trim())
      .filter(name => name.length > 0)
      .join(', ');
  
    this.selectedCategoryName.set('');
  
    if (selected.length !== 3) {
      this.formData['category_id'] = null;
      return;
    }
  
    const ageGroups = selected.map(athlete =>
      this.getAgeGroup(Number(athlete['age']))
    );
  
    if (ageGroups.some(group => group === null)) {
      this.formData['category_id'] = null;
      this.error.set('У одного или нескольких спортсменов не определён допустимый возраст.');
      return;
    }
  
    const uniqueGroups = [...new Set(ageGroups)];
  
    if (uniqueGroups.length !== 1) {
      this.formData['category_id'] = null;
      this.error.set('Нельзя объединить спортсменов из разных возрастных категорий.');
      return;
    }
  
    const ageGroup = uniqueGroups[0]!;
    const expectedName = this.getCategoryName(ageGroup);
  
    const category = this.categories().find(item =>
      String(item['name'] ?? '').trim().toLowerCase() ===
      expectedName.toLowerCase()
    );
  
    if (!category) {
      this.formData['category_id'] = null;
      this.error.set(`В справочнике категорий не найдена категория «${expectedName}».`);
      return;
    }
  
    this.formData['category_id'] = category.id;
    this.selectedCategoryName.set(expectedName);
    this.error.set('');
  }
  

  isNumberField(field: KataGroupField): boolean {
    const type = field.type.toLowerCase();

    return type.includes('float') ||
      type.includes('numeric') ||
      type.includes('integer');
  }

  isDateField(field: KataGroupField): boolean {
    return field.type.toLowerCase().includes('date');
  }

  save(): void {   
    if (this.selectedAthleteIds().length !== 3) {
      this.error.set('В ката-группе должно быть ровно три спортсмена');
      return;
    } 
    if (!this.formData['category_id']) {
      this.error.set('Не удалось определить возрастную категорию группы.');
      return;
    }
    
    if (!this.formData['name']) {
      this.error.set('Не удалось сформировать название группы.');
      return;
    }

    const data: KataGroupPayload = {
      ...this.formData,
      athlete_ids: this.selectedAthleteIds()
    };

    delete data['id'];
    delete data['athletes'];
    delete data['athlete_count'];
    delete data['is_complete'];

    this.saving.set(true);
    this.error.set('');

    const request = this.editingId()
      ? this.service.update(
          this.tournamentId,
          this.editingId()!,
          data
        )
      : this.service.create(this.tournamentId, data);

    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.closeForm();
        this.load();
      },
      error: err => {
        console.error(err);
        this.error.set(
          err.error?.detail || 'Ошибка сохранения ката-группы'
        );
        this.saving.set(false);
      }
    });
  }

  remove(group: KataGroup): void {
    if (!confirm('Удалить эту ката-группу?')) {
      return;
    }

    this.service.delete(this.tournamentId, group.id).subscribe({
      next: () => this.load(),
      error: err => {
        console.error(err);
        this.error.set('Не удалось удалить ката-группу');
      }
    });
  }
}
