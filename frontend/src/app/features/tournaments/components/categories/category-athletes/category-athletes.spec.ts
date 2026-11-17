import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CategoryAthletes } from './category-athletes';

describe('CategoryAthletes', () => {
  let component: CategoryAthletes;
  let fixture: ComponentFixture<CategoryAthletes>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CategoryAthletes],
    }).compileComponents();

    fixture = TestBed.createComponent(CategoryAthletes);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
