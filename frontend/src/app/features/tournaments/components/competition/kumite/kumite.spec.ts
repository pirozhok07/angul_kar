import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Kumite } from './kumite';

describe('Kumite', () => {
  let component: Kumite;
  let fixture: ComponentFixture<Kumite>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Kumite],
    }).compileComponents();

    fixture = TestBed.createComponent(Kumite);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
