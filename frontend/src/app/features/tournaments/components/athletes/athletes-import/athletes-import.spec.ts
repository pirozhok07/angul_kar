import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AthletesImport } from './athletes-import';

describe('AthletesImport', () => {
  let component: AthletesImport;
  let fixture: ComponentFixture<AthletesImport>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AthletesImport],
    }).compileComponents();

    fixture = TestBed.createComponent(AthletesImport);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
