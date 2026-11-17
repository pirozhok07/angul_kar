import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CategoriesDistribution } from './categories-distribution';

describe('CategoriesDistribution', () => {
  let component: CategoriesDistribution;
  let fixture: ComponentFixture<CategoriesDistribution>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CategoriesDistribution],
    }).compileComponents();

    fixture = TestBed.createComponent(CategoriesDistribution);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
